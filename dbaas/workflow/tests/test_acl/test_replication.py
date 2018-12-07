# coding: utf-8
from mock import patch
from django.test import TestCase

from physical.models import Instance
from physical.tests import factory as physical_factory
from dbaas_credentials.tests import factory as credential_factory
from dbaas_credentials.models import CredentialType
from workflow.steps.util.acl import ReplicateAcls2NewInstance


__all__ = ('ReplicatingNewInstanceTestCase',)


class ReplicatingNewInstanceTestCase(TestCase):
    def _create_instance(self):
        inst = Instance()
        inst.address = '127.0.0.1'
        inst.port = 27017
        inst.is_active = True
        inst.databaseinfra = physical_factory.DatabaseInfraFactory.create(
            plan=self.plan
        )
        inst.status = 1
        inst.instance_type = 2
        inst.total_size_in_bytes = 100
        inst.used_size_in_bytes = 50
        #TODO: Fix that vm_name. See better way to set vm_name not on instance directly
        inst.vm_name = inst.dns

        return inst

    @patch('workflow.steps.util.acl.AclClient')
    def setUp(self, client_mock):
        self.weaker_offering = physical_factory.OfferingFactory.create(
            name='weaker_offering',
            memory_size_mb=1,
            cpus=1
        )
        self.stronger_offering = physical_factory.OfferingFactory.create(
            name='stronger_offering',
            memory_size_mb=9,
            cpus=9
        )
        self.plan = physical_factory.PlanFactory(
            weaker_offering=self.weaker_offering,
            stronger_offering=self.stronger_offering
        )
        self.instance = self._create_instance()
        self.infra = self.instance.databaseinfra
        self.env = self.infra.environment

        self.credential = credential_factory.CredentialFactory.create(
            integration_type__name='Fake ACLAPI',
            integration_type__type=CredentialType.ACLAPI,
            endpoint='fake_endpoint',
            user='fake_user',
            password='fake_password',
            project='fake_project'
        )

        self.credential.environments.add(self.env)

        self.step_instance = ReplicateAcls2NewInstance(self.instance)
        self.client_mock = client_mock

    def test_init_client(self):
        self.assertTrue(self.client_mock.called)
        call_args = self.client_mock.call_args[0]
        self.assertEqual(call_args[0], 'fake_endpoint')
        self.assertEqual(call_args[1], 'fake_user')
        self.assertEqual(call_args[2], 'fake_password')
        self.assertEqual(call_args[3].id, self.env.id)
        self.assertEqual(self.step_instance.acl_client, self.client_mock())

    @patch('workflow.steps.util.acl.AclClient')
    def test_init_no_client(self, client_mock):
        self.credential.environments.remove(self.env)
        self.step_instance = ReplicateAcls2NewInstance(self.instance)
        self.assertFalse(client_mock.called)
        self.assertEqual(self.step_instance.acl_client, None)
