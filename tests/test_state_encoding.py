import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from alisa_cli import state

class Encoding(unittest.TestCase):
 def test_cyrillic_phrases_survive_save_and_load_in_any_locale(self):
  # Windows reads text as cp1251 by default; the saved file is UTF-8.
  c=state.defaults('native');c['host']='192.0.2.10';c['phrases']['open']='открой чат'
  with tempfile.TemporaryDirectory() as folder,patch.object(state,'HOME',Path(folder)):
   state.save(c)
   with patch('locale.getpreferredencoding',return_value='cp1251'),patch('locale.getencoding',return_value='cp1251',create=True):
    loaded=state.load('native')
  self.assertEqual(loaded['phrases']['open'],'открой чат')
  self.assertEqual(state.command_file(loaded['phrases']).decode().splitlines()[0],'1\tоткрой чат')

 def test_three_ask_aliases_are_prefix_actions(self):
  lines=state.command_file(state.DEFAULT_PHRASES).decode().splitlines()
  self.assertEqual(lines.count('5\tспроси у чата'),1)
  self.assertEqual(lines.count('5\tспроси у джипити'),1)
  self.assertEqual(lines.count('5\tспроси у чатджипити'),1)
  self.assertEqual(state.normalize_phrase('Алиса, СПРОСИ У ДЖИПИТИ!'),'спроси у джипити')

 def test_old_config_without_ask_aliases_is_migrated_on_load(self):
  old=state.defaults('native');old['host']='192.0.2.10'
  for key in state.ASK_PHRASE_KEYS:old['phrases'].pop(key)
  with tempfile.TemporaryDirectory() as folder,patch.object(state,'HOME',Path(folder)):
   (Path(folder)/'native').mkdir(parents=True)
   (Path(folder)/'native/config.json').write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
   loaded=state.load('native')
  self.assertEqual(loaded['phrases']['ask'],'спроси у чата')
  self.assertEqual(loaded['phrases']['ask_gpt'],'спроси у джипити')
  self.assertEqual(loaded['phrases']['ask_chatgpt'],'спроси у чатджипити')

 def test_ask_aliases_must_differ_from_each_other(self):
  phrases=dict(state.DEFAULT_PHRASES);phrases['ask_gpt']=phrases['ask']
  with self.assertRaises(ValueError):state.command_file(phrases)

 def test_migration_does_not_shadow_an_existing_custom_phrase(self):
  old=state.defaults('native');old['host']='192.0.2.10';old['phrases']['open']='спроси у чата'
  for key in state.ASK_PHRASE_KEYS:old['phrases'].pop(key)
  with tempfile.TemporaryDirectory() as folder,patch.object(state,'HOME',Path(folder)):
   (Path(folder)/'native').mkdir(parents=True)
   (Path(folder)/'native/config.json').write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
   loaded=state.load('native')
  self.assertNotIn('ask',loaded['phrases'])
  self.assertEqual(loaded['phrases']['ask_gpt'],'спроси у джипити')
  self.assertNotIn('5\tспроси у чата\n'.encode(),state.command_file(loaded['phrases']))

if __name__=='__main__':unittest.main()
