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

 def test_every_default_ask_variant_is_a_prefix_action(self):
  lines=state.command_file(state.DEFAULT_PHRASES).decode().splitlines()
  for text in state.DEFAULT_ASK_PHRASES:
   self.assertEqual(lines.count('5\t'+text),1,text)
  self.assertEqual(sum(line.startswith('5\t') for line in lines),len(state.DEFAULT_ASK_PHRASES))
  self.assertEqual(state.normalize_phrase('Алиса, СПРОСИ У ДЖИПИТИ!'),'спроси у джипити')

 def test_old_config_without_ask_aliases_is_migrated_on_load(self):
  old=state.defaults('native');old['host']='192.0.2.10'
  old['phrases'].pop('ask')
  with tempfile.TemporaryDirectory() as folder,patch.object(state,'HOME',Path(folder)):
   (Path(folder)/'native').mkdir(parents=True)
   (Path(folder)/'native/config.json').write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
   loaded=state.load('native')
  self.assertEqual(loaded['phrases']['ask'],list(state.DEFAULT_ASK_PHRASES))

 def test_first_one_shot_config_with_separate_keys_is_merged(self):
  old=state.defaults('native');old['host']='192.0.2.10'
  old['phrases']['ask']='спроси у чата'
  old['phrases']['ask_gpt']='спроси у джипити'
  old['phrases']['ask_chatgpt']='спроси у чатджипити'
  with tempfile.TemporaryDirectory() as folder,patch.object(state,'HOME',Path(folder)):
   (Path(folder)/'native').mkdir(parents=True)
   (Path(folder)/'native/config.json').write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
   loaded=state.load('native')
  self.assertEqual(loaded['phrases']['ask'],list(state.DEFAULT_ASK_PHRASES))
  self.assertNotIn('ask_gpt',loaded['phrases']);self.assertNotIn('ask_chatgpt',loaded['phrases'])

 def test_ask_variants_must_differ_from_each_other_and_other_actions(self):
  phrases=dict(state.DEFAULT_PHRASES);phrases['ask']=['спроси у чата','спроси у чата']
  with self.assertRaises(ValueError):state.command_file(phrases)
  phrases['ask']=['спроси у чата','открой чат']
  with self.assertRaises(ValueError):state.command_file(phrases)

 def test_explicit_ask_list_is_respected_without_restoring_defaults(self):
  c=state.defaults('native');c['host']='192.0.2.10';c['phrases']['ask']=['спроси у нейросети']
  with tempfile.TemporaryDirectory() as folder,patch.object(state,'HOME',Path(folder)):
   state.save(c);loaded=state.load('native')
  self.assertEqual(loaded['phrases']['ask'],['спроси у нейросети'])
  self.assertEqual(state.command_file(loaded['phrases']).decode().count('5\t'),1)

 def test_migration_does_not_shadow_an_existing_custom_phrase(self):
  old=state.defaults('native');old['host']='192.0.2.10';old['phrases']['open']='спроси у чата'
  old['phrases'].pop('ask')
  with tempfile.TemporaryDirectory() as folder,patch.object(state,'HOME',Path(folder)):
   (Path(folder)/'native').mkdir(parents=True)
   (Path(folder)/'native/config.json').write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
   loaded=state.load('native')
  self.assertNotIn('спроси у чата',loaded['phrases']['ask'])
  self.assertIn('спроси у нейросети',loaded['phrases']['ask'])
  self.assertNotIn('5\tспроси у чата\n'.encode(),state.command_file(loaded['phrases']))

 def test_parse_phrase_list_accepts_commas_semicolons_and_newlines(self):
  self.assertEqual(state.parse_phrase_list('спроси у чата, спроси чатик;спроси чат\nспроси у нейросети'),
                   ['спроси у чата','спроси чатик','спроси чат','спроси у нейросети'])

if __name__=='__main__':unittest.main()
