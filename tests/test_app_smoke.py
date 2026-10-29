import sys
from pathlib import Path
import unittest
APP = str(Path(__file__).resolve().parents[1] / "app_parking.py")
from unittest.mock import patch, Mock
from streamlit.testing.v1 import AppTest
from services.parking_domain import bangkok_now
class Sheet:
 def __init__(self,book,title,id,rows):
  self.spreadsheet=book;self.title=title;self.id=id;self.rows=rows;self.row_count=1000
 def get(self,range):
  if self.title=='Settings': return self.rows[1:] if range.startswith('A2') else self.rows
  if range == 'N1:N': return [[r[13]] if len(r)>13 else [] for r in self.rows]
  width=14 if range.endswith('N') else 4
  return [r[:width] for r in self.rows]
 def add_rows(self,n):self.row_count+=n
class Book:
 def __init__(self):
  self.raw=Sheet(self,'RawData',42,[['วันที่ตรวจพบ','อาคาร','ทะเบียนรถ','จังหวัด']+['']*9+['record_id'],['']*4+['FORMULA']*9])
  self.settings=Sheet(self,'Settings',43,[['อาคาร'],['อาคาร 4']])
 def worksheet(self,name):return {'RawData':self.raw,'Settings':self.settings}[name]
 def worksheets(self):return [self.raw,self.settings]
 def values_batch_get(self,ranges):return {'valueRanges':[{'values':[r[:4] for r in self.raw.rows]}]}
 def batch_update(self,body):
  for request in body['requests']:
   if 'updateCells' in request:
    u=request['updateCells'];s=u['start'];sheet=self.raw if s['sheetId']==42 else self.settings
    for offset,row in enumerate(u['rows']):
     i=s['rowIndex']+offset
     while len(sheet.rows)<=i:sheet.rows.append([])
     while len(sheet.rows[i])<s['columnIndex']+len(row['values']):sheet.rows[i].append('')
     for j,c in enumerate(row['values']):sheet.rows[i][s['columnIndex']+j]=next(iter(c.get('userEnteredValue',{'stringValue':''}).values()))
   if 'repeatCell' in request:
    r=request['repeatCell']['range']
    for i in range(r['startRowIndex'],r['endRowIndex']):self.raw.rows[i][:4]=['']*4

class AppSmokeTests(unittest.TestCase):
 def test_save_and_cancel_preserve_formula_anchors(self):
  book=Book();client=Mock();client.open_by_url.return_value=book
  with patch('gspread.authorize',return_value=client),patch('google.oauth2.service_account.Credentials.from_service_account_info',return_value=Mock()):
   at=AppTest.from_file(APP)
   at.secrets['gcp_service_account']={};at.secrets['spreadsheet_url']='https://example.invalid/test'
   at.run(timeout=30)
   assert not at.exception,list(at.exception)
   [t for t in at.text_input if t.label=='ทะเบียนรถยนต์'][0].input('กก1234');at.run(timeout=30)
   [b for b in at.button if b.label=='บันทึกข้อมูลเข้าสู่ระบบ'][0].click();at.run(timeout=30)
   assert not at.exception,list(at.exception)
   assert book.raw.rows[1][0]==bangkok_now().strftime('%Y-%m-%d'),book.raw.rows
   assert book.raw.rows[1][13],book.raw.rows
   [b for b in at.button if b.label=='ยกเลิกชุดล่าสุด'][0].click();at.run(timeout=30)
   assert not at.exception,list(at.exception)
   assert book.raw.rows[1][0]  # Clicking cancel alone must not delete anything.
   [b for b in at.button if b.label=='ยืนยันยกเลิกชุดล่าสุด'][0].click();at.run(timeout=30)
   assert book.raw.rows[1][:4]==['']*4
   assert book.raw.rows[1][4:13]==['FORMULA']*9
   print('PASS: actual Streamlit AppTest load -> save -> UUID -> cancel; formula anchors preserved; no external data written')
