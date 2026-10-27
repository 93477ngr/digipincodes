import test from "node:test";
import assert from "node:assert/strict";
import {getDigiPin,getLatLngFromDigiPin} from "../src/digipin.js";
test("DIGIPIN uses ten approved symbols",()=>assert.match(getDigiPin(17.4065,78.4772),/^[23456789CJKLMPFT]{10}$/));
test("decoded cell center encodes to same cell",()=>{const pin=getDigiPin(17.4065,78.4772);const ll=getLatLngFromDigiPin(pin);assert.equal(getDigiPin(ll.latitude,ll.longitude),pin);});
test("rejects out-of-bounds coordinate",()=>assert.throws(()=>getDigiPin(0,0),/coverage/));
test("rejects malformed code",()=>assert.throws(()=>getLatLngFromDigiPin("bad"),/Invalid/));
