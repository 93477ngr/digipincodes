// Adapted from India Post's open-source reference implementation.
// Upstream: https://github.com/INDIAPOST-gov/digipin
export const GRID=[["F","C","9","8"],["J","3","2","7"],["K","4","5","6"],["L","M","P","T"]];
export const BOUNDS={minLat:2.5,maxLat:38.5,minLon:63.5,maxLon:99.5};
export function getDigiPin(lat,lon){
 if(!Number.isFinite(lat)||!Number.isFinite(lon))throw new TypeError("Coordinates must be finite numbers.");
 if(lat<BOUNDS.minLat||lat>BOUNDS.maxLat||lon<BOUNDS.minLon||lon>BOUNDS.maxLon)throw new RangeError("Coordinate is outside DIGIPIN coverage.");
 let a=BOUNDS.minLat,b=BOUNDS.maxLat,c=BOUNDS.minLon,d=BOUNDS.maxLon,out="";
 for(let i=0;i<10;i++){const h=(b-a)/4,w=(d-c)/4;let r=3-Math.floor((lat-a)/h),col=Math.floor((lon-c)/w);r=Math.max(0,Math.min(3,r));col=Math.max(0,Math.min(3,col));out+=GRID[r][col];b=a+h*(4-r);a=a+h*(3-r);const nextLonMin=c+w*col,nextLonMax=c+w*(col+1);c=nextLonMin;d=nextLonMax;}
 return out;
}
export function getLatLngFromDigiPin(value){
 if(typeof value!=="string"||!/^[23456789CJKLMPFT]{10}$/i.test(value.trim()))throw new Error("Invalid 10-character DIGIPIN.");
 let a=BOUNDS.minLat,b=BOUNDS.maxLat,c=BOUNDS.minLon,d=BOUNDS.maxLon;
 for(const ch of value.trim().toUpperCase()){let r=-1,col=-1;for(let i=0;i<4;i++)for(let j=0;j<4;j++)if(GRID[i][j]===ch){r=i;col=j;}if(r<0)throw Error("Invalid DIGIPIN symbol.");const h=(b-a)/4,w=(d-c)/4;const na=b-h*(r+1),nb=b-h*r,nc=c+w*col,nd=c+w*(col+1);a=na;b=nb;c=nc;d=nd;}
 return {latitude:(a+b)/2,longitude:(c+d)/2};
}
