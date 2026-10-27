#!/usr/bin/env python3
"""Fetch LGD village-with-PIN records from data.gov.in and shard them for web search.
Set DATA_GOV_KEY from your registered data.gov.in API account. No key is embedded.
"""
import collections,json,os,pathlib,re,sys,time,requests
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"public"/"data"
RESOURCE="f17a1608-5f10-4610-bb50-a63c80d83974"
URL="https://api.data.gov.in/resource/"+RESOURCE
STATES=[1,2,3,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,27,28,29,30,31,32,33,34,35,36,37,38]
def normalize(s):return re.sub(r"\\s+"," ",str(s or "")).strip().casefold()
def shard_key(name):
 chars=[c for c in normalize(name) if c.isalnum()]
 return "".join(chars[:2]) if len(chars)>1 else ("".join(chars)+"_") if chars else "__"
def get_page(session,params):
 for attempt in range(7):
  try:
   res=session.get(URL,params=params,timeout=90,headers={"User-Agent":"digipincodes-directory-builder/1.0"})
   if res.status_code in (429,500,502,503,504):raise requests.HTTPError(str(res.status_code),response=res)
   res.raise_for_status();return res.json()
  except (requests.RequestException,ValueError):
   if attempt==6:raise
   time.sleep(min(2**attempt*2,45))
def main():
 key=os.environ.get("DATA_GOV_KEY")
 if not key:sys.exit("Set DATA_GOV_KEY. Register at https://data.gov.in/.")
 villages={}
 with requests.Session() as session:
  for state in STATES:
   offset=0;expected=None;seen=0
   while True:
    data=get_page(session,{"api-key":key,"format":"json","limit":1000,"offset":offset,"filters[stateCode]":state,"sort[villageCode]":"asc"})
    recs=data.get("records") or []
    if expected is None:expected=int(data.get("total") or 0)
    if not recs:break
    for row in recs:
     code=str(row.get("villageCode") or "").strip();name=str(row.get("villageNameEnglish") or "").strip()
     if not code or not name:continue
     v=villages.setdefault(code,{"id":code,"name":name,"stateCode":str(row.get("stateCode") or ""),"state":str(row.get("stateNameEnglish") or ""),"districtCode":str(row.get("districtCode") or ""),"district":str(row.get("districtNameEnglish") or ""),"subdistrictCode":str(row.get("subdistrictCode") or ""),"subdistrict":str(row.get("subdistrictNameEnglish") or ""),"pins":set()})
     pin=str(row.get("pincode") or "").strip()
     if len(pin)==6 and pin.isdigit():v["pins"].add(pin)
    seen+=len(recs)
    if expected and seen>=expected:break
    offset+=len(recs)
   print("state",state,"seen",seen,"expected",expected)
   if expected and seen<expected:raise RuntimeError("Incomplete response for state "+str(state)+": refusing partial export")
 if not villages:raise RuntimeError("API returned no village rows.")
 name_shards=collections.defaultdict(list);pin_map=collections.defaultdict(list)
 for v in villages.values():
  v["pins"]=sorted(v["pins"]);name_shards[shard_key(v["name"])].append(v)
  for pin in v["pins"]:pin_map[pin].append(v["id"])
 (OUT/"villages").mkdir(parents=True,exist_ok=True);(OUT/"pins").mkdir(parents=True,exist_ok=True)
 for key,items in name_shards.items():
  items.sort(key=lambda x:(normalize(x["name"]),x["state"],x["district"],x["subdistrict"],x["id"]))
  (OUT/"villages"/(key+".json")).write_text(json.dumps(items,ensure_ascii=False,separators=(",",":")),"utf-8")
 pin_shards=collections.defaultdict(dict)
 for pin,ids in pin_map.items():pin_shards[pin[:2]][pin]=sorted(set(ids))
 for key,items in pin_shards.items():(OUT/"pins"/(key+".json")).write_text(json.dumps(items,separators=(",",":")),"utf-8")
 meta={"schemaVersion":1,"generatedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source":"data.gov.in LGD - Villages with PIN Codes","resourceId":RESOURCE,"villageRecords":len(villages),"villageShards":{k:len(v) for k,v in name_shards.items()},"pinCount":len(pin_map),"pinShards":sorted(pin_shards),"note":"Only PINs explicitly published in source records are included; no inferred mapping."}
 (OUT/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
 print("Built",len(villages),"unique LGD village codes and",len(pin_map),"PIN assignments")
if __name__=="__main__":main()
