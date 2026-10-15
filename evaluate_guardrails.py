"""Offline contract evaluation. Does not measure a language model's factual quality."""
import copy
import json
import pathlib
import rental_radar as rr


def evaluate():
    evidence = json.loads((pathlib.Path(__file__).parent / "sample/evidence.json").read_text())
    source = evidence["records"]["311"][0]["source_id"]
    valid = {"summary": [{"text": "The supplied record is a complaint.", "source_ids": [source]}],
             "viewing_questions": [{"text": "What follow-up documentation is available?", "source_ids": [source]}],
             "limitations": ["Complaint records do not establish current conditions."]}
    cases=[]
    for i in range(5):
        item=copy.deepcopy(valid);item["summary"][0]["source_ids"]=[f"invented:{i}"]
        cases.append((f"unknown-summary-id-{i}",item,False))
    for i in range(5):
        item=copy.deepcopy(valid);item["viewing_questions"][0]["source_ids"]=[f"invented:{i}"]
        cases.append((f"unknown-question-id-{i}",item,False))
    for field in ["summary", "viewing_questions"]:
        for text in ["", " ", "\n"]:
            item=copy.deepcopy(valid);item[field][0]["text"]=text
            cases.append((f"blank-{field}-{repr(text)}",item,False))
    for field in ["summary", "viewing_questions"]:
        item=copy.deepcopy(valid);item[field][0]["source_ids"]=[]
        cases.append((f"missing-citation-{field}",item,False))
    for source_id in evidence["aggregate_source_ids"]:
        item=copy.deepcopy(valid);item["viewing_questions"][0]["source_ids"]=[source_id]
        cases.append((f"aggregate-question-{source_id}",item,False))
    for r in evidence["records"]["311"][:4]:
        item=copy.deepcopy(valid)
        item["summary"][0]["source_ids"]=[r["source_id"]]
        item["viewing_questions"][0]["source_ids"]=[r["source_id"]]
        cases.append((f"valid-citation-{r['source_id']}",item,True))
    results=[]
    for name,payload,expected in cases:
        try:
            rr.validate_llm(payload,evidence);accepted=True
        except (ValueError,KeyError,TypeError):
            accepted=False
        results.append({"case":name,"expected_accept":expected,"accepted":accepted,"passed":accepted==expected})
    return {"evaluation_type":"offline schema/citation contract checks, not external LLM evaluation", "total":len(results),
            "passed":sum(x["passed"] for x in results),"cases":results,
            "not_evaluated":["claim entailment","prompt-injection resistance of a model","usefulness to renters","latency","actual token usage and cost"]}


if __name__=='__main__':
    result=evaluate()
    target=pathlib.Path(__file__).parent/'model_artifacts_validated'/'guardrail_contract_results.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))
    if result['passed']!=result['total']:raise SystemExit(1)
