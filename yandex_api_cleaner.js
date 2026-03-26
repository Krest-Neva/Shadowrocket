let body = $response.body;
const url = $request.url;
if (body) {
try {
let obj = JSON.parse(body);
let modified = false;
const adKeys = ['ads','adverts','banners','badv','promoted','native_ads','direct','sponsor'];
if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
adKeys.forEach(key => {
if (obj[key] !== undefined) { delete obj[key]; modified = true; }
});
}
function removeAdsFromArray(arr) {
if (!Array.isArray(arr)) return arr;
const initialLength = arr.length;
const filtered = arr.filter(item => {
if (!item || typeof item !== 'object') return true;
return !(item.type === 'ad' || item.type === 'banner' || item.is_ad === true || item.is_promoted === true || item.is_sponsor === true || item.ad_info);
});
if (filtered.length !== initialLength) modified = true;
return filtered;
}
['data','items','results','feed','toponyms'].forEach(key => {
if (obj[key] && Array.isArray(obj[key])) {
obj[key] = removeAdsFromArray(obj[key]);
}
});
if (obj.fact?.badv) { delete obj.fact.badv; modified = true; }
if (obj.forecast?.badv) { delete obj.forecast.badv; modified = true; }
if (obj.searchResult?.results) {
obj.searchResult.results = removeAdsFromArray(obj.searchResult.results);
}
if (modified) body = JSON.stringify(obj);
} catch (e) {
console.log("Yandex API Cleaner Error: " + e);
}
}
$done({ body });