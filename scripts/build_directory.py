#!/usr/bin/env python3
"""Build all-LGD village name shards and source-listed PIN crosswalk assets.
Needs DATA_GOV_KEY; uses a pinned public export of the LGD master village roster
plus data.gov.in's official LGD villages-with-PIN resource.
"""
import collections,io,json,os,pathlib,re,sys,time,unicodedata,requests
import pandas as pd
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"data"
RESOURCE="f17a1608-5f10-4610-bb50-a63c80d83974"
API="https://api.data.gov.in/resource/"+RESOURCE
# Versioned public mirror of a government-exported LGD village roster. Its metadata documents source, checksum and row count.
ROSTER_URL="https://raw.githubusercontent.com/vanga/india-local-government-directory/d43ab199f27e472f64f88d291a7cf9511aa899ed/data/lgd_villages.parquet"
def norm(s):
 # Keep this key algorithm in sync with src/app.js browser normalization.
 value=unicodedata.normalize("NFKD",str(s or ""))
 value="".join(ch for ch in value if not unicodedata.combining(ch))
 value=value.encode("ascii","ignore").decode("ascii").lower()
 return re.sub(r"[^a-z0-9]+"," ",value).strip()
def key_for(s):
 chars=[c for c in norm(s) if c.isalnum()]
 return "".join(chars[:2]) if len(chars)>1 else ("".join(chars)+"_") if chars else "__"
def get_json(session,params):
 for attempt in range(7):
  try:
   r=session.get(API,params=params,timeout=90,headers={"User-Agent":"digipincodes-directory-builder/1.0"})
   if r.status_code in (429,500,502,503,504):raise requests.HTTPError(str(r.status_code),response=r)
   r.raise_for_status();return r.json()
  except (requests.RequestException,ValueError):
   if attempt==6:raise
   time.sleep(min(2**attempt*2,45))
def main():
 token=os.environ.get("DATA_GOV_KEY")
 if not token:sys.exit("Set DATA_GOV_KEY. Register at https://data.gov.in/.")
 with requests.Session() as session:
  res=session.get(ROSTER_URL,timeout=120,headers={"User-Agent":"digipincodes-directory-builder/1.0"});res.raise_for_status()
  frame=pd.read_parquet(io.BytesIO(res.content))
 villages={}
 for row in frame.to_dict(orient="records"):
  code=str(row.get("village_code") or "").strip();name=str(row.get("village_name") or "").strip()
  if not code or not name:continue
  villages[code]={"id":code,"name":name,"stateCode":str(row.get("state_code") or ""),"state":str(row.get("state_name") or ""),"districtCode":str(row.get("district_code") or ""),"district":str(row.get("district_name") or ""),"subdistrictCode":str(row.get("subdistrict_code") or ""),"subdistrict":str(row.get("subdistrict_name") or ""),"localName":str(row.get("local_language_name") or ""),"pins":set()}
 print("Loaded LGD roster rows:",len(villages))
 # Join only source-published PIN associations, keeping multi-PIN assignments.
 state_codes=sorted({int(v["stateCode"]) for v in villages.values() if v["stateCode"].isdigit()})
 seen_links=0
 with requests.Session() as session:
  for state in state_codes:
   offset=0;expected=None;got=0
   while True:
    data=get_json(session,{"api-key":token,"format":"json","limit":1000,"offset":offset,"filters[stateCode]":state,"sort[villageCode]":"asc"})
    recs=data.get("records") or []
    if expected is None:expected=int(data.get("total") or 0)
    if not recs:break
    for row in recs:
     code=str(row.get("villageCode") or "").strip()
     if not code:continue
     pin=str(row.get("pincode") or "").strip()
     if len(pin)!=6 or not pin.isdigit():continue
     if code not in villages:
      # Include a feed record that postdates the pinned master roster snapshot.
      villages[code]={"id":code,"name":str(row.get("villageNameEnglish") or ""),"stateCode":str(row.get("stateCode") or ""),"state":str(row.get("stateNameEnglish") or ""),"districtCode":str(row.get("districtCode") or ""),"district":str(row.get("districtNameEnglish") or ""),"subdistrictCode":str(row.get("subdistrictCode") or ""),"subdistrict":str(row.get("subdistrictNameEnglish") or ""),"localName":"","pins":set()}
     villages[code]["pins"].add(pin);seen_links+=1
    got+=len(recs)
    if expected and got>=expected:break
    offset+=len(recs)
   print("PIN crosswalk state",state,"rows",got,"expected",expected)
   if expected and got<expected:raise RuntimeError("Incomplete data.gov.in page sequence for state "+str(state))
 name_shards=collections.defaultdict(list);pin_map=collections.defaultdict(list)
 for v in villages.values():
  v["pins"]=sorted(v["pins"])
  if not v["name"]:continue
  name_shards[key_for(v["name"])].append(v)
  for pin in v["pins"]:pin_map[pin].append({"id":v["id"],"name":v["name"],"subdistrict":v["subdistrict"],"district":v["district"],"state":v["state"]})
 (OUT/"villages").mkdir(parents=True,exist_ok=True);(OUT/"pins").mkdir(parents=True,exist_ok=True)
 for key,items in name_shards.items():
  items.sort(key=lambda v:(norm(v["name"]),v["state"],v["district"],v["subdistrict"],v["id"]))
  (OUT/"villages"/(key+".json")).write_text(json.dumps(items,ensure_ascii=False,separators=(",",":")),"utf-8")
 pin_shards=collections.defaultdict(dict)
 for pin,records in pin_map.items():
  unique={v["id"]:v for v in records}
  pin_shards[pin[:2]][pin]=sorted(unique.values(),key=lambda v:(norm(v["name"]),v["state"],v["district"],v["id"]))
 for key,items in pin_shards.items():(OUT/"pins"/(key+".json")).write_text(json.dumps(items,ensure_ascii=False,separators=(",",":")),"utf-8")
 meta={"schemaVersion":1,"generatedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"sourceRoster":"LGD village export mirror, pinned revision d43ab199f27e472f64f88d291a7cf9511aa899ed (see upstream metadata)","postalSource":"data.gov.in LGD - Villages with PIN Codes","resourceId":RESOURCE,"villageRecords":len(villages),"villageShards":{k:len(v) for k,v in name_shards.items()},"pinCount":len(pin_map),"pinShards":sorted(pin_shards),"publishedPinLinksRead":seen_links,"note":"Roster villages without source PIN associations remain searchable. Only source-listed PINs are shown; no mapping is inferred."}
 (OUT/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
 print("Built",len(villages),"LGD village IDs;",len(pin_map),"PINs;",seen_links,"source PIN links.")
if __name__=="__main__":main()
