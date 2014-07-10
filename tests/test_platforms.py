import unittest

from vmmaster.core.platform import Platforms
from vmmaster.core.config import config, setup_config
from vmmaster.core.virtual_machine.virtual_machine import VirtualMachine
from vmmaster.core.exceptions import PlatformException


class TestPlatforms(unittest.TestCase):
    def setUp(self):
        setup_config('data/config.py')
        self.platforms = Platforms()
        self.platform = "test_origin_1"

    def tearDown(self):
        self.platforms.delete()

    def test_platforms_count(self):
        self.assertEqual(2, len(self.platforms.platforms))

    def test_vm_creation(self):
        self.assertEqual(0, self.platforms.vm_count)
        vm = self.platforms.create(self.platform)
        self.assertIsInstance(vm, VirtualMachine)
        self.assertEqual(1, self.platforms.vm_count)

    def test_vm_deletion(self):
        vm = self.platforms.create(self.platform)
        self.assertEqual(1, self.platforms.vm_count)
        vm.delete()
        self.assertEqual(0, self.platforms.vm_count)

    def test_max_vm_count(self):
        config.MAX_VM_COUNT = 2

        self.platforms.create(self.platform)
        self.platforms.create(self.platform)
        with self.assertRaises(PlatformException) as e:
            self.platforms.create(self.platform)

        the_exception = e.exception
        self.assertEqual("maximum count of virtual machines already running", the_exception.message)