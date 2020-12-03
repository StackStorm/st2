def test_resolve_urls(self):
        url = eval_repo_url(
            "https://github.com/StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "https://github.com/StackStorm-Exchange/stackstorm-test")

        url = eval_repo_url(
            "https://github.com/StackStorm-Exchange/stackstorm-test.git")
        self.assertEqual(url, "https://github.com/StackStorm-Exchange/stackstorm-test.git")

        url = eval_repo_url("StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "https://github.com/StackStorm-Exchange/stackstorm-test")

        url = eval_repo_url("git://StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "git://StackStorm-Exchange/stackstorm-test")

        url = eval_repo_url("git://StackStorm-Exchange/stackstorm-test.git")
        self.assertEqual(url, "git://StackStorm-Exchange/stackstorm-test.git")

        url = eval_repo_url("git@github.com:foo/bar.git")
        self.assertEqual(url, "git@github.com:foo/bar.git")

        url = eval_repo_url("file:///home/vagrant/stackstorm-test")
        self.assertEqual(url, "file:///home/vagrant/stackstorm-test")

        url = eval_repo_url("file://localhost/home/vagrant/stackstorm-test")
        self.assertEqual(url, "file://localhost/home/vagrant/stackstorm-test")

        url = eval_repo_url('ssh://<user@host>/AutomationStackStorm')
        self.assertEqual(url, 'ssh://<user@host>/AutomationStackStorm')

        url = eval_repo_url('ssh://joe@local/AutomationStackStorm')
        self.assertEqual(url, 'ssh://joe@local/AutomationStackStorm')

    def test_run_pack_download_edge_cases(self):
        """
        Edge cases to test:

        default branch is master, ref is pack version
        default branch is master, ref is branch name
        default branch is master, ref is default branch name
        default branch is not master, ref is pack version
        default branch is not master, ref is branch name
        default branch is not master, ref is default branch name
        """

        def side_effect(ref):
            if ref[0] != 'v':
                raise BadName()
            return mock.MagicMock(hexsha='abcdeF')

        self.repo_instance.commit.side_effect = side_effect

        edge_cases = [
            ('master', '1.2.3'),
            ('master', 'some-branch'),
            ('master', 'default-branch'),
            ('master', None),
            ('default-branch', '1.2.3'),
            ('default-branch', 'some-branch'),
            ('default-branch', 'default-branch'),
            ('default-branch', None)
        ]

        for default_branch, ref in edge_cases:
            self.repo_instance.git = mock.MagicMock(
                branch=(lambda *args: default_branch),
                checkout=(lambda *args: True)
            )

            # Set default branch
            self.repo_instance.active_branch.name = default_branch
            self.repo_instance.active_branch.object = 'aBcdef'
            self.repo_instance.head.commit = 'aBcdef'

            # Fake gitref object
            gitref = mock.MagicMock(hexsha='abcDef')

            # Fool _get_gitref into working when its ref == our ref
            def fake_commit(arg_ref):
                if not ref or arg_ref == ref:
                    return gitref
                else:
                    raise BadName()
            self.repo_instance.commit = fake_commit
            self.repo_instance.active_branch.object = gitref

            action = self.get_action_instance()

            if ref:
                packs = ['test=%s' % (ref)]
            else:
                packs = ['test']

            result = action.run(packs=packs, abs_repo_base=self.repo_base)
            self.assertEqual(result, {'test': 'Success.'})

    @mock.patch('os.path.isdir', mock_is_dir_func)
    def test_run_pack_dowload_local_git_repo_detached_head_state(self):
        action = self.get_action_instance()

        type(self.repo_instance).active_branch = \
            mock.PropertyMock(side_effect=TypeError('detached head'))

        pack_path = os.path.join(BASE_DIR, 'fixtures/stackstorm-test')

        result = action.run(packs=['file://%s' % (pack_path)], abs_repo_base=self.repo_base)
        self.assertEqual(result, {'test': 'Success.'})

        # Verify function has bailed out early
        self.repo_instance.git.checkout.assert_not_called()
        self.repo_instance.git.branch.assert_not_called()
        self.repo_instance.git.checkout.assert_not_called()

    def test_run_pack_download_local_directory(self):
        action = self.get_action_instance()

        # 1. Local directory doesn't exist
        expected_msg = r'Local pack directory ".*" doesn\'t exist'
        self.assertRaisesRegexp(ValueError, expected_msg, action.run,
                                packs=['file://doesnt_exist'], abs_repo_base=self.repo_base)

        # 2. Local pack which is not a git repository
        pack_path = os.path.join(BASE_DIR, 'fixtures/stackstorm-test4')

        result = action.run(packs=['file://%s' % (pack_path)], abs_repo_base=self.repo_base)
        self.assertEqual(result, {'test4': 'Success.'})

        # Verify pack contents have been copied over
        destination_path = os.path.join(self.repo_base, 'test4')
        self.assertTrue(os.path.exists(destination_path))
        self.assertTrue(os.path.exists(os.path.join(destination_path, 'pack.yaml')))

    @mock.patch('st2common.util.pack_management.get_gitref', mock_get_gitref)
    def test_run_pack_download_with_tag(self):
        action = self.get_action_instance()
        result = action.run(packs=['test'], abs_repo_base=self.repo_base)
        temp_dir = hashlib.md5(PACK_INDEX['test']['repo_url'].encode()).hexdigest()

        self.assertEqual(result, {'test': 'Success.'})
        self.clone_from.assert_called_once_with(PACK_INDEX['test']['repo_url'],
                                                os.path.join(os.path.expanduser('~'), temp_dir))
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, 'test/pack.yaml')))

        # Check repo.git.checkout is called three times
        self.assertEqual(self.repo_instance.git.checkout.call_count, 3)

        # Check repo.git.checkout called with latest tag or branch
        self.assertEqual(PACK_INDEX['test']['version'],
                         self.repo_instance.git.checkout.call_args_list[1][0][0])

        # Check repo.git.checkout called with head
        self.assertEqual(self.repo_instance.head.reference,
                         self.repo_instance.git.checkout.call_args_list[2][0][0])

        self.repo_instance.git.branch.assert_called_with(
            '-f', self.repo_instance.head.reference, PACK_INDEX['test']['version'])
