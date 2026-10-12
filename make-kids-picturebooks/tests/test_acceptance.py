import json,shutil,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

SKILL=Path(__file__).resolve().parents[1]

def complete_project(root, blank_page=None):
 def write(path,data):
  (root/path).write_text(json.dumps(data,ensure_ascii=False) if not isinstance(data,str) else data,encoding='utf-8')
 write('source.txt','source A')
 (root/'characters').mkdir();write('characters/ref.txt','character reference')
 shutil.copy(SKILL/'assets/kidsbook-print.ttf',root/'font.ttf')
 shutil.copy(SKILL/'assets/font-license.txt',root/'font-license.txt')
 write('font-provenance.txt','synthetic font provenance')
 Image.new('RGB',(1600,2400),'white').save(root/'test-image.png')
 pages=[]
 for i,kind in enumerate(('cover','story','story','back'),1):
  if i==blank_page:kind='blank'
  pages.append({'number':i,'kind':kind,'text':'' if i==blank_page else '小朋友。','image':'test-image.png','image_box_mm':[10,10,128,190],'text_box_mm':[14,120,120,76],'image_role':'background','text_area_reviewed':True})
 write('layout.json',{'font_path':'font.ttf','font_license_path':'font-license.txt','font_provenance_path':'font-provenance.txt','pages':pages})
 write('concept.json',{'book_id':'b1','age_band':'5-7'});write('story.txt',''.join(page['text'] for page in pages if page['kind']=='story'));write('storyboard.json',{'pages':pages})
 manifest_pages=[]
 for i,page in enumerate(pages,1):
  manifest_pages.append({'page':i,'text_version':'v1','characters_version':'v1','character_reference_path':'characters/ref.txt','text_area':page['text_box_mm'],'current_prompt_path':'prompt.txt','current_image_path':'test-image.png','props':[],'knowledge_check':{'status':'passed','evidence':'synthetic test fixture'},'previous_page_state':{'state_id':'story_start' if i==1 else f'page-{i-1:02d}-hook','summary':f'Synthetic state before page {i}.'},'current_page_entry':{'state_id':'page-01-entry' if i==1 else f'page-{i-1:02d}-hook','summary':f'Synthetic entry state for page {i}.'},'next_page_hook':{'state_id':'story_end' if i==len(pages) else f'page-{i:02d}-hook','summary':f'Synthetic hook after page {i}.'},'text_image_match':{'status':'passed','evidence':f'Synthetic text and image review for page {i}.'},'continuity_review':{'status':'passed','evidence':f'Synthetic continuity review for page {i}.'}})
 write('manifest.json',{'schema_version':1,'book_id':'b1','age_band':'5-7','pages':manifest_pages})
 write('prompt.txt','synthetic test only')
 from export_book import export_book
 export_book(root/'layout.json',root/'export')
 write('review.json',{'reading_pages':[{'page':i,'status':'passed','evidence':'synthetic test only','image_path':f'export/reading-pages/page-{i:02}.png'} for i in range(1,5)],'print_sides':[{'side':i,'status':'passed','evidence':'synthetic test only','image_path':f'export/print-pages/page-{i:02}.png'} for i in range(1,3)],'unresolved_digital_defects':[]})
 write('project.json',{'schema_version':1,'target_age_bands':['5-7'],'source':{'path':'source.txt','version':'v1','coverage':'synthetic'},'characters_version':'v1','characters_path':'characters','books':[{'id':'b1','age_band':'5-7','source_version':'v1','characters_version':'v1','status':'laid_out','artifacts':{'concept':'concept.json','story':'story.txt','storyboard':'storyboard.json','layout':'layout.json','page_manifest':'manifest.json','reading_pdf':'export/reading.pdf','print_pdf':'export/print.pdf','review':'review.json'}}]})
 return root/'project.json'

class AcceptanceTests(unittest.TestCase):
 def test_acceptance_allows_an_explicit_blank_page(self):
  from accept_book import check_book
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   try:project_path=complete_project(root,blank_page=3)
   except (TypeError,ValueError) as exc:self.fail(f'explicit blank page should export: {exc}')
   self.assertEqual(check_book(project_path,'b1')['errors'],[])
 def test_acceptance_requires_each_page_character_reference(self):
  from accept_book import check_book
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);project_path=complete_project(root);manifest=read_json(root/'manifest.json')
   del manifest['pages'][0]['character_reference_path'];write_json(root/'manifest.json',manifest)
   errors=check_book(project_path,'b1')['errors']
   self.assertTrue(any('pages[1].character_reference_path' in error for error in errors),errors)
 def test_acceptance_rejects_missing_character_reference_file(self):
  from accept_book import check_book
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);project_path=complete_project(root);manifest=read_json(root/'manifest.json')
   manifest['pages'][0]['character_reference_path']='characters/missing.txt';write_json(root/'manifest.json',manifest)
   errors=check_book(project_path,'b1')['errors']
   self.assertTrue(any('pages[1].character_reference_path' in error for error in errors),errors)
 def test_acceptance_rejects_stale_character_reference_directory(self):
  from accept_book import check_book
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);project_path=complete_project(root)
   (root/'characters-v0').mkdir();(root/'characters-v0/ref.txt').write_text('stale reference',encoding='utf-8')
   manifest=read_json(root/'manifest.json');manifest['pages'][0]['character_reference_path']='characters-v0/ref.txt';write_json(root/'manifest.json',manifest)
   errors=check_book(project_path,'b1')['errors']
   self.assertIn('页1: 角色参考不在当前批准目录 characters',errors)
 def test_acceptance_rejects_out_of_project_character_reference(self):
  from accept_book import check_book
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);project_path=complete_project(root)
   outside=root.parent/f'{root.name}-outside-reference.txt';outside.write_text('outside reference',encoding='utf-8')
   self.addCleanup(outside.unlink,missing_ok=True)
   manifest=read_json(root/'manifest.json');manifest['pages'][0]['character_reference_path']=str(outside);write_json(root/'manifest.json',manifest)
   errors=check_book(project_path,'b1')['errors']
   self.assertTrue(any('pages[1].character_reference_path' in error and 'project' in error for error in errors),errors)
 def test_acceptance_rejects_final_print_text_below_minimum(self):
  from accept_book import check_book
  import pymupdf as fitz
  from impose_booklet import MM
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);project_path=complete_project(root)
   font=root/'font.ttf';texts=['小朋友。']*4;printing=root/'export/print.pdf';document=fitz.open()
   for left,right in ((4,1),(2,3)):
    page=document.new_page(width=297*MM,height=210*MM)
    page.insert_font(fontname='kidsbook',fontfile=str(font))
    page.insert_text((36,54),texts[left-1],fontsize=17,fontname='kidsbook')
    page.insert_text((page.rect.width/2+36,54),texts[right-1],fontsize=17,fontname='kidsbook')
   document.save(printing);document.close()
   self.assertIn('print page 1: text size 17.0 pt is below 18.0 pt',check_book(project_path,'b1')['errors'])
 def test_acceptance_requires_declared_font_license_and_provenance(self):
  from accept_book import check_book
  for field,label in (('font_license_path','字体许可证'),('font_provenance_path','字体来源证明')):
   with self.subTest(field=field),tempfile.TemporaryDirectory() as td:
    root=Path(td);project_path=complete_project(root);layout=json.loads((root/'layout.json').read_text(encoding='utf-8'))
    del layout[field];(root/'layout.json').write_text(json.dumps(layout,ensure_ascii=False),encoding='utf-8')
    self.assertIn(f'验收版面须保存项目内{label}路径',check_book(project_path,'b1')['errors'])
 def test_hash_receipt_rejects_changed_file(self):
  from accept_book import verify_receipt
  import hashlib
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'story.md').write_text('original',encoding='utf-8')
   project={'source':{'version':'v1'},'characters_version':'v1'}
   book={'id':'b1','age_band':'3-4','source_version':'v1','characters_version':'v1','artifacts':{'acceptance':'receipt.json'}}
   receipt={'schema_version':1,'book_id':'b1','age_band':'3-4','source_version':'v1','characters_version':'v1','files':{'story.md':hashlib.sha256((root/'story.md').read_bytes()).hexdigest()}}
   (root/'receipt.json').write_text(json.dumps(receipt),encoding='utf-8')
   self.assertEqual(verify_receipt(project,book,root),[])
   (root/'story.md').write_text('changed',encoding='utf-8')
   self.assertTrue(verify_receipt(project,book,root))
 def test_missing_receipt_does_not_claim_completion(self):
  from accept_book import verify_receipt
  with tempfile.TemporaryDirectory() as td:
   self.assertTrue(verify_receipt({}, {'artifacts':{'acceptance':'missing.json'}},Path(td)))
 def test_quality_requires_explicit_pilot_choice(self):
  from accept_book import quality_errors
  self.assertTrue(quality_errors({'target_dpi':200}))
  self.assertTrue(quality_errors({'quality_profile':'home-pilot','target_dpi':200}))
  self.assertEqual(quality_errors({'quality_profile':'home-pilot','target_dpi':200,'quality_approval':'用户选择家庭试制200'}),[])
  self.assertEqual(quality_errors({'target_dpi':300}),[])
 def test_complete_book_requires_story_and_covers(self):
  from accept_book import structure_errors
  self.assertTrue(structure_errors([{'kind':'parents'}]*4))
  self.assertEqual(structure_errors([{'kind':'cover'},{'kind':'story'},{'kind':'parents'},{'kind':'back'}]),[])
 def test_receipt_detects_changed_source_path_without_version_bump(self):
  from accept_book import verify_receipt
  import hashlib
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'source.txt').write_text('a',encoding='utf-8');(root/'other.txt').write_text('b',encoding='utf-8')
   project={'source':{'path':'source.txt','version':'v1'},'characters_version':'v1','characters_path':'characters/v1'}
   book={'id':'b1','age_band':'3-4','artifacts':{'acceptance':'receipt.json'}}
   receipt={'schema_version':1,'book_id':'b1','age_band':'3-4','source_version':'v1','characters_version':'v1','source_path':'source.txt','characters_path':'characters/v1','files':{'source.txt':hashlib.sha256((root/'source.txt').read_bytes()).hexdigest()}}
   (root/'receipt.json').write_text(json.dumps(receipt),encoding='utf-8')
   self.assertEqual(verify_receipt(project,book,root),[])
   project['source']['path']='other.txt'
   self.assertTrue(verify_receipt(project,book,root))

def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def write_json(path,data):path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':unittest.main()
