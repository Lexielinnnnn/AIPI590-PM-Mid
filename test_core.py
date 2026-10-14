import unittest
from rental_radar import summarize, validate_llm, literal
class Checks(unittest.TestCase):
 def test_scope_and_status(self):
  rows=[{'unique_key':'1','agency':'HPD','complaint_type':'HEAT/HOT WATER','status':'Closed','created_date':'2026-01-01'}, {'unique_key':'2','agency':'NYPD','complaint_type':'Noise - Residential','status':'Open'}, {'unique_key':'3','agency':'DOT','complaint_type':'Street Condition'}]
  selected,c=summarize(rows)
  self.assertEqual(c['eligible_requests'],2);self.assertEqual(c['excluded_requests'],1)
  self.assertEqual(c['by_status'],{'Closed':1,'Open':1});self.assertEqual(c['missing_closed_date'],2)
 def test_empty(self): self.assertEqual(summarize([])[1]['latest_created'],None)
 def test_duplicate_fails(self):
  with self.assertRaises(ValueError): summarize([{'unique_key':'1'},{'unique_key':'1'}])
 def test_unknown_citation_fails(self):
  with self.assertRaises(ValueError): validate_llm({'summary':[{'text':'Claim','source_ids':['invented']}],'viewing_questions':[]},{'records':[]})
 def test_query_literal(self): self.assertEqual(literal("O'BRIEN"),"'O''BRIEN'")
if __name__=='__main__': unittest.main()
