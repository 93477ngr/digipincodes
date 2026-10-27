import test from "node:test";
import assert from "node:assert/strict";
import {getDigiPin,getLatLngFromDigiPin} from "../src/digipin.js";
test("matches India Post published encoder example",()=>assert.equal(getDigiPin(13.11179621,80.20264269),"4T396F42L7"));
test("decoder returns a valid center coordinate",()=>{const ll=getLatLngFromDigiPin("4T396F42L7");assert.ok(ll.latitude>=2.5&&ll.latitude<=38.5);assert.ok(ll.longitude>=63.5&&ll.longitude<=99.5);});
test("rejects out-of-bounds coordinate",()=>assert.throws(()=>getDigiPin(0,0),/coverage/));
test("rejects malformed code",()=>assert.throws(()=>getLatLngFromDigiPin("bad"),/Invalid/));
