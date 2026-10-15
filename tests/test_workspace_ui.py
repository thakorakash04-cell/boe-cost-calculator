import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from workspace_store import Store

class WorkspaceUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.url='sqlite:///'+str(Path(self.tmp.name)/'ui.db')
        self.env=patch.dict(os.environ,{'DATABASE_URL':self.url,'ADMIN_USERNAME':'admin_user','ADMIN_PASSWORD':'Test-only-admin-password!123'})
        self.env.start()
        self.store=Store(self.url);self.store.bootstrap_admin('admin_user','Test-only-admin-password!123')
        self.admin=self.store.login('admin_user','Test-only-admin-password!123')
        self.store.create_viewer(self.admin,'viewer_user','Test-only-viewer-password!123')
    def tearDown(self):
        self.env.stop();self.tmp.cleanup()
    def signed_in(self,username,password):
        at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
        self.assertEqual(len(at.exception),0)
        self.assertFalse(at.get('component_instance'))
        at.text_input(key='login_username').set_value(username)
        at.text_input(key='login_password').set_value(password)
        at.button[0].click().run()
        self.assertEqual(len(at.exception),0)
        return at
    def test_viewer_has_no_management_or_downloads(self):
        at=self.signed_in('viewer_user','Test-only-viewer-password!123')
        self.assertFalse(any(t.label=='Manage users' for t in at.toggle))
        self.assertEqual(len(at.get('download_button')),0)
        self.assertEqual(len(at.get('file_uploader')),0)
        self.assertEqual(len(at.get('data_editor')),0)
    def test_admin_manage_users_and_revocation(self):
        at=self.signed_in('admin_user','Test-only-admin-password!123')
        at.toggle(key='workspace_users').set_value(True).run()
        self.assertEqual(len(at.exception),0)
        self.assertTrue(any(t.label=='New viewer username' for t in at.text_input))
        self.store.bootstrap_admin('admin_user','Rotated-password!123')
        at.run()
        self.assertTrue(any(t.label=='Username' for t in at.text_input))

if __name__=='__main__':unittest.main()

class BOEResultTests(WorkspaceUITests):
    def test_saved_result_loads_for_viewer_after_restart(self):
        from calculation_engine import compute_boe_costing
        result=compute_boe_costing({'exchange_rate':83.5,'invoice_value_fc':100,'total_weight_kg':1},[{'material_name':'Sample','quantity':10,'unit_price_fc':10,'bcd_rate_percent':7.5,'sws_rate_percent':10,'igst_rate_percent':18}])
        self.store.save_dataset(self.admin,'BOE calculation',{'results':result})
        reopened=Store(self.url)
        self.assertEqual(reopened.get_dataset(self.admin)['data']['results'],result)
        at=self.signed_in('viewer_user','Test-only-viewer-password!123')
        self.assertEqual(at.session_state['computed_results'],result)
        self.assertEqual(len(at.get('component_instance')),2)
        self.assertEqual(len(at.get('download_button')),0)
        self.assertEqual(len(at.get('file_uploader')),0)
