#!/usr/bin/env python3
"""Build searchable nationwide LGD villages, admin areas and source-listed PIN crosswalk.
The public roster is buildable without a data.gov.in key. Exact postal links are joined
only when DATA_GOV_KEY is configured; otherwise any previous published PIN index is kept.
"""
import collections,io,json,os,pathlib,re,sys,time,unicodedata,requests
import pandas as pd
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"data"
RESOURCE="f17a1608-5f10-4610-bb50-a63c80d83974"
API="https://api.data.gov.in/resource/"+RESOURCE
ROSTER_URL="https://raw.githubusercontent.com/vanga/india-local-government-directory/d43ab199f27e472f64f88d291a7cf9511aa899ed/data/lgd_villages.parquet"
def norm(s):
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
def read_existing_links():
 links=collections.defaultdict(set)
 folder=OUT/"pins"
 if not folder.exists():return links
 for path in folder.glob("*.json"):
  try:
   payload=json.loads(path.read_text("utf-8"))
   for pin,rows in payload.items():
    if len(pin)==6 and pin.isdigit():
     for row in rows:
      if row.get("id"):links[str(row["id"])].add(pin)
  except (OSError,ValueError,AttributeError):raise RuntimeError("Existing PIN shard unreadable: "+str(path))
 return links
def main():
 token=os.environ.get("DATA_GOV_KEY","").strip()
 with requests.Session() as session:
  res=session.get(ROSTER_URL,timeout=120,headers={"User-Agent":"digipincodes-directory-builder/1.0"});res.raise_for_status()
  frame=pd.read_parquet(io.BytesIO(res.content))
 villages={}
 for row in frame.to_dict(orient="records"):
  code=str(row.get("village_code") or "").strip();name=str(row.get("village_name") or "").strip()
  if not code or not name:continue
  villages[code]={"id":code,"name":name,"stateCode":str(row.get("state_code") or ""),"state":str(row.get("state_name") or ""),"districtCode":str(row.get("district_code") or ""),"district":str(row.get("district_name") or ""),"subdistrictCode":str(row.get("subdistrict_code") or ""),"subdistrict":str(row.get("subdistrict_name") or ""),"localName":str(row.get("local_language_name") or ""),"pins":set()}
 if not villages:raise RuntimeError("LGD master roster returned no village rows; refusing empty export.")
 print("Loaded unique LGD roster villages:",len(villages))
 links=read_existing_links()
 if token:
  print("Refreshing source PIN links using data.gov.in")
  links=collections.defaultdict(set)
  state_codes=sorted({int(v["stateCode"]) for v in villages.values() if v["stateCode"].isdigit()})
  with requests.Session() as session:
   for state in state_codes:
    offset=0;expected=None;got=0
    while True:
     data=get_json(session,{"api-key":token,"format":"json","limit":1000,"offset":offset,"filters[stateCode]":state,"sort[villageCode]":"asc"})
     recs=data.get("records") or []
     if expected is None:expected=int(data.get("total") or 0)
     if not recs:break
     for row in recs:
      code=str(row.get("villageCode") or "").strip();pin=str(row.get("pincode") or "").strip()
      if not code or len(pin)!=6 or not pin.isdigit():continue
      if code not in villages:
       villages[code]={"id":code,"name":str(row.get("villageNameEnglish") or ""),"stateCode":str(row.get("stateCode") or ""),"state":str(row.get("stateNameEnglish") or ""),"districtCode":str(row.get("districtCode") or ""),"district":str(row.get("districtNameEnglish") or ""),"subdistrictCode":str(row.get("subdistrictCode") or ""),"subdistrict":str(row.get("subdistrictNameEnglish") or ""),"localName":"","pins":set()}
      links[code].add(pin);got+=1
     got_page=len(recs);offset+=got_page
     if expected and offset>=expected:break
    print("PIN source state",state,"rows consumed",offset,"source total",expected)
    if expected and offset<expected:raise RuntimeError("Incomplete data.gov.in pagination for state "+str(state))
  pin_mode="source refreshed"
 else:
  print("DATA_GOV_KEY not set. Keeping prior PIN links (if any); building full searchable LGD roster.")
  pin_mode="previous snapshot retained" if any(links.values()) else "not configured"
 for code,pins in links.items():
  if code in villages:villages[code]["pins"].update(p for p in pins if len(p)==6 and p.isdigit())
 name_shards=collections.defaultdict(list);pin_map=collections.defaultdict(list);area_groups=collections.defaultdict(dict)
 for v in villages.values():
  v["pins"]=sorted(v["pins"])
  if not v["name"]:continue
  name_shards[key_for(v["name"])].append(v)
  for pin in v["pins"]:pin_map[pin].append({"id":v["id"],"name":v["name"],"subdistrict":v["subdistrict"],"district":v["district"],"state":v["state"]})
  member={"id":v["id"],"name":v["name"],"stateCode":v["stateCode"],"state":v["state"],"districtCode":v["districtCode"],"district":v["district"],"subdistrictCode":v["subdistrictCode"],"subdistrict":v["subdistrict"],"pins":v["pins"]}
  if v["subdistrictCode"] and v["subdistrict"]:
   aid="sub:"+v["subdistrictCode"];ent=area_groups[aid].setdefault("record",{"id":aid,"kind":"mandal","name":v["subdistrict"],"district":v["district"],"state":v["state"],"villages":[]});ent["villages"].append(member)
  if v["districtCode"] and v["district"]:
   aid="district:"+v["districtCode"];ent=area_groups[aid].setdefault("record",{"id":aid,"kind":"district","name":v["district"],"state":v["state"],"villages":[]});ent["villages"].append(member)
 for directory in ("villages","pins","areas"):(OUT/directory).mkdir(parents=True,exist_ok=True)
 for key,items in name_shards.items():
  items.sort(key=lambda v:(norm(v["name"]),v["state"],v["district"],v["subdistrict"],v["id"]))
  (OUT/"villages"/(key+".json")).write_text(json.dumps(items,ensure_ascii=False,separators=(",",":")),"utf-8")
 area_shards=collections.defaultdict(list)
 for item in area_groups.values():
  area=item["record"];area["villages"].sort(key=lambda v:(norm(v["name"]),v["state"],v["district"],v["id"]));area_shards[key_for(area["name"])].append(area)
 for key,items in area_shards.items():
  items.sort(key=lambda a:(norm(a["name"]),a["kind"],a["state"],a["district"],a["id"]))
  (OUT/"areas"/(key+".json")).write_text(json.dumps(items,ensure_ascii=False,separators=(",",":")),"utf-8")
 pin_shards=collections.defaultdict(dict)
 for pin,records in pin_map.items():
  pin_shards[pin[:2]][pin]=sorted({v["id"]:v for v in records}.values(),key=lambda v:(norm(v["name"]),v["state"],v["district"],v["id"]))
 for key,items in pin_shards.items():(OUT/"pins"/(key+".json")).write_text(json.dumps(items,ensure_ascii=False,separators=(",",":")),"utf-8")
 meta={"schemaVersion":1,"generatedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"sourceRoster":"LGD village export mirror, pinned revision d43ab199f27e472f64f88d291a7cf9511aa899ed","postalSource":"data.gov.in LGD - Villages with PIN Codes","resourceId":RESOURCE,"pinMappingStatus":pin_mode,"villageRecords":len(villages),"villageShards":{k:len(v) for k,v in name_shards.items()},"areaShards":{k:len(v) for k,v in area_shards.items()},"pinCount":len(pin_map),"pinShards":sorted(pin_shards),"note":"LGD village snapshot, not a promise that all habitations are included. Postal PINs are source-listed only; no mapping is inferred."}
 (OUT/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
 print("Exported",len(villages),"LGD village IDs,",len(area_groups),"admin areas,",len(pin_map),"PINs; mapping:",pin_mode)
if __name__=="__main__":main()
