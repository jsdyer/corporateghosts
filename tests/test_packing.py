import gzip,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from packing import pack,version_assets
class PackingTests(unittest.TestCase):
 def test_changed_records_have_different_shard_names_and_readable_data(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'data').mkdir();a=pack(root,'active','Active',[[1,'a']]);b=pack(root,'active','Active',[[1,'b']]);self.assertNotEqual(a['shards'],b['shards']);self.assertEqual(json.loads(gzip.decompress((root/'data'/b['shards'][0]).read_bytes())),[[1,'b']])
 def test_html_import_worker_and_manifest_share_version(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'data').mkdir();(root/'data/manifest.json').write_text('{}');(root/'index.html').write_text('<script src="./app.js"></script>');(root/'app.js').write_text('import "./live.mjs"; fetch("./data/manifest.json"); new URL("./worker.js",import.meta.url)');(root/'live.mjs').write_text('');(root/'worker.js').write_text('');v=version_assets(root);self.assertIn('app.js?v='+v,(root/'index.html').read_text());text=(root/'app.js').read_text();self.assertIn('live.mjs?v='+v,text);self.assertIn('manifest.json?v='+v,text);self.assertIn('worker.js?v='+v,text)
