# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module for syncing RBAC definitions in the database with the ones from the filesystem.
"""

from st2common import log as logging
from st2common.models.db.auth import UserDB
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.services import rbac as rbac_services
from st2common.util.uid import parse_uid


LOG = logging.getLogger(__name__)

__all__ = [
    'RBACDefinitionsDBSyncer'
]


class RBACDefinitionsDBSyncer(object):
    """
    A class which makes sure that the role definitions and user role assignments in the database
    match ones specified in the role definition files.

    The class works by simply deleting all the obsolete roles (either removed or updated) and
    creating new roles (either new roles or one which have been updated).

    Note #1: Our current datastore doesn't support transactions or similar which means that with
    the current data model there is a short time frame during sync when the definitions inside the
    DB are out of sync with the ones in the file.

    Note #2: The operation of this class is idempotent meaning that if it's ran multiple time with
    the same dataset, the end result / outcome will be the same.
    """

    def sync(self, role_definition_apis, role_assignment_apis):
        """
        Synchronize all the role definitions and user role assignments.
        """
        result = {}

        result['roles'] = self.sync_roles(role_definition_apis)
        result['role_assignments'] = self.sync_users_role_assignments(role_assignment_apis)

        return result

    def sync_roles(self, role_definition_apis):
        """
        Synchronize all the role definitions in the database.

        :param role_dbs: RoleDB objects for the roles which are currently in the database.
        :type role_dbs: ``list`` of :class:`RoleDB`

        :param role_definition_apis: RoleDefinition API objects for the definitions loaded from
                                     the files.
        :type role_definition_apis: ``list`` of :class:RoleDefinitionFileFormatAPI`

        :rtype: ``tuple``
        """
        LOG.info('Synchronizing roles...')

        # Retrieve all the roles currently in the DB
        role_dbs = rbac_services.get_all_roles(exclude_system=True)

        role_db_names = [role_db.name for role_db in role_dbs]
        role_db_names = set(role_db_names)
        role_api_names = [role_definition_api.name for role_definition_api in role_definition_apis]
        role_api_names = set(role_api_names)

        # A list of new roles which should be added to the database
        new_role_names = role_api_names.difference(role_db_names)

        # A list of roles which need to be updated in the database
        updated_role_names = role_db_names.intersection(role_api_names)

        # A list of roles which should be removed from the database
        removed_role_names = (role_db_names - role_api_names)

        LOG.debug('New roles: %r' % (new_role_names))
        LOG.debug('Updated roles: %r' % (updated_role_names))
        LOG.debug('Removed roles: %r' % (removed_role_names))

        # Build a list of roles to delete
        role_names_to_delete = updated_role_names.union(removed_role_names)
        role_dbs_to_delete = [role_db for role_db in role_dbs if
                              role_db.name in role_names_to_delete]

        # Build a list of roles to create
        role_names_to_create = new_role_names.union(updated_role_names)
        role_apis_to_create = [role_definition_api for role_definition_api in role_definition_apis
                               if role_definition_api.name in role_names_to_create]

        ########
        # 1. Remove obsolete roles and associated permission grants from the DB
        ########

        # Remove roles
        role_ids_to_delete = []
        for role_db in role_dbs_to_delete:
            role_ids_to_delete.append(role_db.id)

        LOG.debug('Deleting %s stale roles' % (len(role_ids_to_delete)))
        Role.query(id__in=role_ids_to_delete, system=False).delete()
        LOG.debug('Deleted %s stale roles' % (len(role_ids_to_delete)))

        # Remove associated permission grants
        permission_grant_ids_to_delete = []
        for role_db in role_dbs_to_delete:
            permission_grant_ids_to_delete.extend(role_db.permission_grants)

        LOG.debug('Deleting %s stale permission grants' % (len(permission_grant_ids_to_delete)))
        PermissionGrant.query(id__in=permission_grant_ids_to_delete).delete()
        LOG.debug('Deleted %s stale permission grants' % (len(permission_grant_ids_to_delete)))

        ########
        # 2. Add new / updated roles to the DB
        ########

        LOG.debug('Creating %s new roles' % (len(role_apis_to_create)))

        # Create new roles
        created_role_dbs = []
        for role_api in role_apis_to_create:
            role_db = rbac_services.create_role(name=role_api.name,
                                                description=role_api.description)

            # Create associated permission grants
            permission_grants = getattr(role_api, 'permission_grants', [])
            for permission_grant in permission_grants:
                resource_uid = permission_grant['resource_uid']
                resource_type, _ = parse_uid(resource_uid)
                permission_types = permission_grant['permission_types']
                assignment_db = rbac_services.create_permission_grant(
                    role_db=role_db,
                    resource_uid=resource_uid,
                    resource_type=resource_type,
                    permission_types=permission_types)

                role_db.permission_grants.append(str(assignment_db.id))
            created_role_dbs.append(role_db)

        LOG.debug('Created %s new roles' % (len(created_role_dbs)))
        LOG.info('Roles synchronized (%s created, %s updated, %s removed)' %
                 (len(new_role_names), len(updated_role_names), len(removed_role_names)))

        return [created_role_dbs, role_dbs_to_delete]

    def sync_users_role_assignments(self, role_assignment_apis):
        """
        Synchronize role assignments for all the users in the database.

        :param role_assignment_apis: Role assignments API objects for the assignments loaded
                                      from the files.
        :type role_assignment_apis: ``list`` of :class:`UserRoleAssignmentFileFormatAPI`

        :return: Dictionary with created and removed role assignments for each user.
        :rtype: ``dict``
        """
        LOG.info('Synchronizing users role assignments...')

        user_dbs = User.get_all()
        username_to_user_db_map = dict([(user_db.name, user_db) for user_db in user_dbs])

        results = {}
        for role_assignment_api in role_assignment_apis:
            username = role_assignment_api.username
            user_db = username_to_user_db_map.get(username, None)

            if not user_db:
                # Note: We allow assignments to be created for the users which don't exist in the
                # DB yet because user creation in StackStorm is lazy (we only create UserDB) object
                # when user first logs in.
                user_db = UserDB(name=username)
                LOG.debug(('User "%s" doesn\'t exist in the DB, creating assignment anyway' %
                          (username)))

            role_assignment_dbs = rbac_services.get_role_assignments_for_user(user_db=user_db)

            result = self._sync_user_role_assignments(user_db=user_db,
                                                      role_assignment_dbs=role_assignment_dbs,
                                                      role_assignment_api=role_assignment_api)
            results[username] = result

        LOG.info('User role assignments synchronized')
        return results

    def _sync_user_role_assignments(self, user_db, role_assignment_dbs, role_assignment_api):
        """
        Synchronize role assignments for a particular user.

        :param user_db: User to synchronize the assignments for.
        :type user_db: :class:`UserDB`

        :param role_assignment_dbs: Existing user role assignments.
        :type role_assignment_dbs: ``list`` of :class:`UserRoleAssignmentDB`

        :param role_assignment_api: Role assignment API for a particular user.
        :param role_assignment_api: :class:`UserRoleAssignmentFileFormatAPI`

        :rtype: ``tuple``
        """
        db_role_names = [role_assignment_db.role for role_assignment_db in role_assignment_dbs]
        db_role_names = set(db_role_names)
        api_role_names = role_assignment_api.roles if role_assignment_api else []
        api_role_names = set(api_role_names)

        # A list of new assignments which should be added to the database
        new_role_names = api_role_names.difference(db_role_names)

        # A list of assgignments which need to be updated in the database
        updated_role_names = db_role_names.intersection(api_role_names)

        # A list of assignments which should be removed from the database
        removed_role_names = (db_role_names - api_role_names)

        LOG.debug('New assignments for user "%s": %r' % (user_db.name, new_role_names))
        LOG.debug('Updated assignments for user "%s": %r' % (user_db.name, updated_role_names))
        LOG.debug('Removed assignments for user "%s": %r' % (user_db.name, removed_role_names))

        # Build a list of role assignments to delete
        role_names_to_delete = updated_role_names.union(removed_role_names)
        role_assignment_dbs_to_delete = [role_assignment_db for role_assignment_db
                                         in role_assignment_dbs
                                         if role_assignment_db.role in role_names_to_delete]

        UserRoleAssignment.query(user=user_db.name, role__in=role_names_to_delete).delete()
        LOG.debug('Removed %s assignments for user "%s"' %
                (len(role_assignment_dbs_to_delete), user_db.name))

        # Build a list of roles assignments to create
        role_names_to_create = new_role_names.union(updated_role_names)
        role_dbs_to_assign = Role.query(name__in=role_names_to_create)

        created_role_assignment_dbs = []
        for role_db in role_dbs_to_assign:
            if role_db.name in role_assignment_api.roles:
                description = getattr(role_assignment_api, 'description', None)
            else:
                description = None
            assignment_db = rbac_services.assign_role_to_user(role_db=role_db, user_db=user_db,
                                                              description=description)
            created_role_assignment_dbs.append(assignment_db)

        LOG.debug('Created %s new assignments for user "%s"' % (len(role_dbs_to_assign),
                                                                user_db.name))

        return (created_role_assignment_dbs, role_assignment_dbs_to_delete)
