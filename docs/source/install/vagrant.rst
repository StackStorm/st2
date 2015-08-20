Vagrant
=================
The following setup with vagrant is tested with `VirtualBox <https://www.virtualbox.org>`_. By default, the setup will install the latest stable release of |st2|. To override that with another version, ``export ST2VER=x.y.z``.

::

    git clone https://github.com/StackStorm/st2express.git
    cd st2express/vagrant/
    vagrant up

This will install all |st2| components along with the Mistral workflow engine on Ubuntu 14.04 virtual machine. Some console output in red is expected and can be safely ignored.  The setup will download additional packages from the internet. While waiting, check out |st2| :doc:`/video` for quick intro. If setup is successful, you will see the following console output. ::

    ==========================================

              _   ___     ____  _  __ 
             | | |__ \   / __ \| |/ / 
          ___| |_   ) | | |  | | ' /  
         / __| __| / /  | |  | |  <   
         \__ \ |_ / /_  | |__| | . \  
         |___/\__|____|  \____/|_|\_\ 

      st2 is installed and ready to use.
    ========================================== 

Use ``vagrant ssh`` to login to the box. 

.. include:: on_complete.rst
