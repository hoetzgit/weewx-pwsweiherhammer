!function(){"use strict";var e={37145:function(e,t,n){var s=this&&this.__awaiter||function(e,t,n,s){return new(n||(n=Promise))((function(a,r){function i(e){try{c(s.next(e))}catch(e){r(e)}}function o(e){try{c(s.throw(e))}catch(e){r(e)}}function c(e){var t;e.done?a(e.value):(t=e.value,t instanceof n?t:new n((function(e){e(t)}))).then(i,o)}c((s=s.apply(e,t||[])).next())}))};Object.defineProperty(t,"__esModule",{value:!0});const a=n(44615),r=n(67162),i=n(69522),o="/offline.html",c=new r.CacheFirst;(0,i.warmStrategyCache)({urls:[o],strategy:c});const u=n(99819),h=n(54065);(0,a.registerRoute)((({request:e})=>"navigate"===e.mode),new r.NetworkFirst({cacheName:"pages",plugins:[new u.CacheableResponsePlugin({statuses:[200]})]})),(0,a.registerRoute)((({request:e})=>"style"===e.destination||"script"===e.destination||"worker"===e.destination),new r.StaleWhileRevalidate({cacheName:"assets",plugins:[new u.CacheableResponsePlugin({statuses:[200]})]})),(0,a.registerRoute)((({request:e})=>"image"===e.destination&&!e.url.includes("dwd/Schilder")&&!e.url.includes("dwd/bwk_bodendruck")),new r.CacheFirst({cacheName:"images",plugins:[new u.CacheableResponsePlugin({statuses:[200]}),new h.ExpirationPlugin({maxEntries:50,maxAgeSeconds:2592e3})]})),(0,a.setCatchHandler)((({event:e})=>s(void 0,void 0,void 0,(function*(){return"document"===e.request.destination?c.handle({event:e,request:o}):Response.error()}))))},35414:function(e,t,n){n.d(t,{v:function(){return s}}),n(87524),n(3125),n(33119),n(70120),n(94895);class s{constructor(e={}){this._statuses=e.statuses,this._headers=e.headers}isResponseCacheable(e){let t=!0;return this._statuses&&(t=this._statuses.includes(e.status)),this._headers&&t&&(t=Object.keys(this._headers).some((t=>e.headers.get(t)===this._headers[t]))),t}}},13709:function(e,t,n){n.d(t,{x:function(){return a}});var s=n(35414);n(94895);class a{constructor(e){this.cacheWillUpdate=async({response:e})=>this._cacheableResponse.isResponseCacheable(e)?e:null,this._cacheableResponse=new s.v(e)}}},94895:function(){try{self["workbox:cacheable-response:6.5.2"]&&_()}catch(e){}},3125:function(e,t,n){n.d(t,{V:function(){return s}}),n(10913);class s extends Error{constructor(e,t){super(((e,...t)=>{let n=e;return t.length>0&&(n+=` :: ${JSON.stringify(t)}`),n})(e,t)),this.name=e,this.details=t}}},87524:function(e,t,n){n(3125),n(10913)},92536:function(e,t,n){n.d(t,{x:function(){return r}}),n(10913);const s={googleAnalytics:"googleAnalytics",precache:"precache-v2",prefix:"workbox",runtime:"runtime",suffix:"undefined"!=typeof registration?registration.scope:""},a=e=>[s.prefix,e,s.suffix].filter((e=>e&&e.length>0)).join("-"),r={updateDetails:e=>{(e=>{for(const t of Object.keys(s))e(t)})((t=>{"string"==typeof e[t]&&(s[t]=e[t])}))},getGoogleAnalyticsName:e=>e||a(s.googleAnalytics),getPrecacheName:e=>e||a(s.precache),getPrefix:()=>s.prefix,getRuntimeName:e=>e||a(s.runtime),getSuffix:()=>s.suffix}},97327:function(e,t,n){function s(e){e.then((()=>{}))}n.d(t,{f:function(){return s}}),n(10913)},33119:function(e,t,n){n.d(t,{C:function(){return s}}),n(10913);const s=e=>new URL(String(e),location.href).href.replace(new RegExp(`^${location.origin}`),"")},70120:function(e,t,n){n.d(t,{k:function(){return s}}),n(10913);const s=null},16902:function(e,t,n){function s(e){return new Promise((t=>setTimeout(t,e)))}n.d(t,{V:function(){return s}}),n(10913)},10913:function(){try{self["workbox:core:6.5.2"]&&_()}catch(e){}},87565:function(e,t,n){n.d(t,{f:function(){return s}}),n(10913);const s=new Set},95400:function(e,t,n){n.d(t,{p:function(){return x}}),n(87524);var s=n(97327);let a,r;n(70120),n(3125);const i=new WeakMap,o=new WeakMap,c=new WeakMap,u=new WeakMap,h=new WeakMap;let l={get(e,t,n){if(e instanceof IDBTransaction){if("done"===t)return o.get(e);if("objectStoreNames"===t)return e.objectStoreNames||c.get(e);if("store"===t)return n.objectStoreNames[1]?void 0:n.objectStore(n.objectStoreNames[0])}return f(e[t])},set:(e,t,n)=>(e[t]=n,!0),has:(e,t)=>e instanceof IDBTransaction&&("done"===t||"store"===t)||t in e};function d(e){return"function"==typeof e?(t=e)!==IDBDatabase.prototype.transaction||"objectStoreNames"in IDBTransaction.prototype?(r||(r=[IDBCursor.prototype.advance,IDBCursor.prototype.continue,IDBCursor.prototype.continuePrimaryKey])).includes(t)?function(...e){return t.apply(p(this),e),f(i.get(this))}:function(...e){return f(t.apply(p(this),e))}:function(e,...n){const s=t.call(p(this),e,...n);return c.set(s,e.sort?e.sort():[e]),f(s)}:(e instanceof IDBTransaction&&function(e){if(o.has(e))return;const t=new Promise(((t,n)=>{const s=()=>{e.removeEventListener("complete",a),e.removeEventListener("error",r),e.removeEventListener("abort",r)},a=()=>{t(),s()},r=()=>{n(e.error||new DOMException("AbortError","AbortError")),s()};e.addEventListener("complete",a),e.addEventListener("error",r),e.addEventListener("abort",r)}));o.set(e,t)}(e),n=e,(a||(a=[IDBDatabase,IDBObjectStore,IDBIndex,IDBCursor,IDBTransaction])).some((e=>n instanceof e))?new Proxy(e,l):e);var t,n}function f(e){if(e instanceof IDBRequest)return function(e){const t=new Promise(((t,n)=>{const s=()=>{e.removeEventListener("success",a),e.removeEventListener("error",r)},a=()=>{t(f(e.result)),s()},r=()=>{n(e.error),s()};e.addEventListener("success",a),e.addEventListener("error",r)}));return t.then((t=>{t instanceof IDBCursor&&i.set(t,e)})).catch((()=>{})),h.set(t,e),t}(e);if(u.has(e))return u.get(e);const t=d(e);return t!==e&&(u.set(e,t),h.set(t,e)),t}const p=e=>h.get(e),g=["get","getKey","getAll","getAllKeys","count"],w=["put","add","delete","clear"],m=new Map;function y(e,t){if(!(e instanceof IDBDatabase)||t in e||"string"!=typeof t)return;if(m.get(t))return m.get(t);const n=t.replace(/FromIndex$/,""),s=t!==n,a=w.includes(n);if(!(n in(s?IDBIndex:IDBObjectStore).prototype)||!a&&!g.includes(n))return;const r=async function(e,...t){const r=this.transaction(e,a?"readwrite":"readonly");let i=r.store;return s&&(i=i.index(t.shift())),(await Promise.all([i[n](...t),a&&r.done]))[0]};return m.set(t,r),r}var _;_=l,l={..._,get:(e,t,n)=>y(e,t)||_.get(e,t,n),has:(e,t)=>!!y(e,t)||_.has(e,t)},n(6550);const v="cache-entries",b=e=>{const t=new URL(e,location.href);return t.hash="",t.href};class R{constructor(e){this._db=null,this._cacheName=e}_upgradeDb(e){const t=e.createObjectStore(v,{keyPath:"id"});t.createIndex("cacheName","cacheName",{unique:!1}),t.createIndex("timestamp","timestamp",{unique:!1})}_upgradeDbAndDeleteOldDbs(e){this._upgradeDb(e),this._cacheName&&function(e,{blocked:t}={}){const n=indexedDB.deleteDatabase(e);t&&n.addEventListener("blocked",(()=>t())),f(n).then((()=>{}))}(this._cacheName)}async setTimestamp(e,t){const n={url:e=b(e),timestamp:t,cacheName:this._cacheName,id:this._getId(e)},s=(await this.getDb()).transaction(v,"readwrite",{durability:"relaxed"});await s.store.put(n),await s.done}async getTimestamp(e){const t=await this.getDb(),n=await t.get(v,this._getId(e));return null==n?void 0:n.timestamp}async expireEntries(e,t){const n=await this.getDb();let s=await n.transaction(v).store.index("timestamp").openCursor(null,"prev");const a=[];let r=0;for(;s;){const n=s.value;n.cacheName===this._cacheName&&(e&&n.timestamp<e||t&&r>=t?a.push(s.value):r++),s=await s.continue()}const i=[];for(const e of a)await n.delete(v,e.id),i.push(e.url);return i}_getId(e){return this._cacheName+"|"+b(e)}async getDb(){return this._db||(this._db=await function(e,t,{blocked:n,upgrade:s,blocking:a,terminated:r}={}){const i=indexedDB.open(e,t),o=f(i);return s&&i.addEventListener("upgradeneeded",(e=>{s(f(i.result),e.oldVersion,e.newVersion,f(i.transaction))})),n&&i.addEventListener("blocked",(()=>n())),o.then((e=>{r&&e.addEventListener("close",(()=>r())),a&&e.addEventListener("versionchange",(()=>a()))})).catch((()=>{})),o}("workbox-expiration",1,{upgrade:this._upgradeDbAndDeleteOldDbs.bind(this)})),this._db}}class x{constructor(e,t={}){this._isRunning=!1,this._rerunRequested=!1,this._maxEntries=t.maxEntries,this._maxAgeSeconds=t.maxAgeSeconds,this._matchOptions=t.matchOptions,this._cacheName=e,this._timestampModel=new R(e)}async expireEntries(){if(this._isRunning)return void(this._rerunRequested=!0);this._isRunning=!0;const e=this._maxAgeSeconds?Date.now()-1e3*this._maxAgeSeconds:0,t=await this._timestampModel.expireEntries(e,this._maxEntries),n=await self.caches.open(this._cacheName);for(const e of t)await n.delete(e,this._matchOptions);this._isRunning=!1,this._rerunRequested&&(this._rerunRequested=!1,(0,s.f)(this.expireEntries()))}async updateTimestamp(e){await this._timestampModel.setTimestamp(e,Date.now())}async isURLExpired(e){if(this._maxAgeSeconds){const t=await this._timestampModel.getTimestamp(e),n=Date.now()-1e3*this._maxAgeSeconds;return void 0===t||t<n}return!1}async delete(){this._rerunRequested=!1,await this._timestampModel.expireEntries(1/0)}}},9491:function(e,t,n){n.d(t,{Q:function(){return c}}),n(87524);var s=n(92536),a=n(97327),r=(n(33119),n(70120),n(87565));n(10913);var i=n(3125),o=n(95400);n(6550);class c{constructor(e={}){var t;this.cachedResponseWillBeUsed=async({event:e,request:t,cacheName:n,cachedResponse:s})=>{if(!s)return null;const r=this._isResponseDateFresh(s),i=this._getCacheExpiration(n);(0,a.f)(i.expireEntries());const o=i.updateTimestamp(t.url);if(e)try{e.waitUntil(o)}catch(e){}return r?s:null},this.cacheDidUpdate=async({cacheName:e,request:t})=>{const n=this._getCacheExpiration(e);await n.updateTimestamp(t.url),await n.expireEntries()},this._config=e,this._maxAgeSeconds=e.maxAgeSeconds,this._cacheExpirations=new Map,e.purgeOnQuotaError&&(t=()=>this.deleteCacheAndMetadata(),r.f.add(t))}_getCacheExpiration(e){if(e===s.x.getRuntimeName())throw new i.V("expire-custom-caches-only");let t=this._cacheExpirations.get(e);return t||(t=new o.p(e,this._config),this._cacheExpirations.set(e,t)),t}_isResponseDateFresh(e){if(!this._maxAgeSeconds)return!0;const t=this._getDateHeaderTimestamp(e);return null===t||t>=Date.now()-1e3*this._maxAgeSeconds}_getDateHeaderTimestamp(e){if(!e.headers.has("date"))return null;const t=e.headers.get("date"),n=new Date(t).getTime();return isNaN(n)?null:n}async deleteCacheAndMetadata(){for(const[e,t]of this._cacheExpirations)await self.caches.delete(e),await t.delete();this._cacheExpirations=new Map}}},6550:function(){try{self["workbox:expiration:6.5.2"]&&_()}catch(e){}},7977:function(){try{self["workbox:precaching:6.5.2"]&&_()}catch(e){}},9144:function(){try{self["workbox:recipes:6.5.2"]&&_()}catch(e){}},74989:function(e,t,n){n.d(t,{t:function(){return a}}),n(87524),n(70120);var s=n(95188);n(39080);class a extends s.A{constructor(e,t,n){super((({url:t})=>{const n=e.exec(t.href);if(n&&(t.origin===location.origin||0===n.index))return n.slice(1)}),t,n)}}},95188:function(e,t,n){n.d(t,{A:function(){return r}}),n(87524);var s=n(91505),a=n(78179);n(39080);class r{constructor(e,t,n=s.g){this.handler=(0,a.M)(t),this.match=e,this.method=n}setCatchHandler(e){this.catchHandler=(0,a.M)(e)}}},71491:function(e,t,n){n.d(t,{F:function(){return i}}),n(87524),n(33119);var s=n(91505),a=(n(70120),n(78179)),r=n(3125);n(39080);class i{constructor(){this._routes=new Map,this._defaultHandlerMap=new Map}get routes(){return this._routes}addFetchListener(){self.addEventListener("fetch",(e=>{const{request:t}=e,n=this.handleRequest({request:t,event:e});n&&e.respondWith(n)}))}addCacheListener(){self.addEventListener("message",(e=>{if(e.data&&"CACHE_URLS"===e.data.type){const{payload:t}=e.data,n=Promise.all(t.urlsToCache.map((t=>{"string"==typeof t&&(t=[t]);const n=new Request(...t);return this.handleRequest({request:n,event:e})})));e.waitUntil(n),e.ports&&e.ports[0]&&n.then((()=>e.ports[0].postMessage(!0)))}}))}handleRequest({request:e,event:t}){const n=new URL(e.url,location.href);if(!n.protocol.startsWith("http"))return;const s=n.origin===location.origin,{params:a,route:r}=this.findMatchingRoute({event:t,request:e,sameOrigin:s,url:n});let i=r&&r.handler;const o=e.method;if(!i&&this._defaultHandlerMap.has(o)&&(i=this._defaultHandlerMap.get(o)),!i)return;let c;try{c=i.handle({url:n,request:e,event:t,params:a})}catch(e){c=Promise.reject(e)}const u=r&&r.catchHandler;return c instanceof Promise&&(this._catchHandler||u)&&(c=c.catch((async s=>{if(u)try{return await u.handle({url:n,request:e,event:t,params:a})}catch(e){e instanceof Error&&(s=e)}if(this._catchHandler)return this._catchHandler.handle({url:n,request:e,event:t});throw s}))),c}findMatchingRoute({url:e,sameOrigin:t,request:n,event:s}){const a=this._routes.get(n.method)||[];for(const r of a){let a;const i=r.match({url:e,sameOrigin:t,request:n,event:s});if(i)return a=i,(Array.isArray(a)&&0===a.length||i.constructor===Object&&0===Object.keys(i).length||"boolean"==typeof i)&&(a=void 0),{route:r,params:a}}return{}}setDefaultHandler(e,t=s.g){this._defaultHandlerMap.set(t,(0,a.M)(e))}setCatchHandler(e){this._catchHandler=(0,a.M)(e)}registerRoute(e){this._routes.has(e.method)||this._routes.set(e.method,[]),this._routes.get(e.method).push(e)}unregisterRoute(e){if(!this._routes.has(e.method))throw new r.V("unregister-route-but-not-found-with-method",{method:e.method});const t=this._routes.get(e.method).indexOf(e);if(!(t>-1))throw new r.V("unregister-route-route-not-registered");this._routes.get(e.method).splice(t,1)}}},39080:function(){try{self["workbox:routing:6.5.2"]&&_()}catch(e){}},5917:function(e,t,n){n.d(t,{X:function(){return o}}),n(70120);var s=n(3125),a=n(95188),r=n(74989),i=n(63486);function o(e,t,n){let o;if("string"==typeof e){const s=new URL(e,location.href),r=({url:e})=>e.href===s.href;o=new a.A(r,t,n)}else if(e instanceof RegExp)o=new r.t(e,t,n);else if("function"==typeof e)o=new a.A(e,t,n);else{if(!(e instanceof a.A))throw new s.V("unsupported-route-type",{moduleName:"workbox-routing",funcName:"registerRoute",paramName:"capture"});o=e}return(0,i.u)().registerRoute(o),o}n(39080)},96226:function(e,t,n){n.d(t,{H:function(){return a}});var s=n(63486);function a(e){(0,s.u)().setCatchHandler(e)}n(39080)},91505:function(e,t,n){n.d(t,{g:function(){return s}}),n(39080);const s="GET"},63486:function(e,t,n){n.d(t,{u:function(){return r}});var s=n(71491);let a;n(39080);const r=()=>(a||(a=new s.F,a.addFetchListener(),a.addCacheListener()),a)},78179:function(e,t,n){n.d(t,{M:function(){return s}}),n(87524),n(39080);const s=e=>e&&"object"==typeof e?e:{handle:e}},44868:function(e,t,n){n.d(t,{b:function(){return r}}),n(87524),n(70120);var s=n(3125),a=n(50951);n(91094),n(76873);class r extends a._{async _handle(e,t){let n,a=await t.cacheMatch(e);if(a);else try{a=await t.fetchAndCachePut(e)}catch(e){e instanceof Error&&(n=e)}if(!a)throw new s.V("no-response",{url:e.url,error:n});return a}}},70495:function(e,t,n){n.d(t,{n:function(){return i}}),n(87524),n(70120);var s=n(3125),a=n(22118),r=n(50951);n(91094),n(76873);class i extends r._{constructor(e={}){super(e),this.plugins.some((e=>"cacheWillUpdate"in e))||this.plugins.unshift(a.S),this._networkTimeoutSeconds=e.networkTimeoutSeconds||0}async _handle(e,t){const n=[],a=[];let r;if(this._networkTimeoutSeconds){const{id:s,promise:i}=this._getTimeoutPromise({request:e,logs:n,handler:t});r=s,a.push(i)}const i=this._getNetworkPromise({timeoutId:r,request:e,logs:n,handler:t});a.push(i);const o=await t.waitUntil((async()=>await t.waitUntil(Promise.race(a))||await i)());if(!o)throw new s.V("no-response",{url:e.url});return o}_getTimeoutPromise({request:e,logs:t,handler:n}){let s;return{promise:new Promise((t=>{s=setTimeout((async()=>{t(await n.cacheMatch(e))}),1e3*this._networkTimeoutSeconds)})),id:s}}async _getNetworkPromise({timeoutId:e,request:t,logs:n,handler:s}){let a,r;try{r=await s.fetchAndCachePut(t)}catch(e){e instanceof Error&&(a=e)}return e&&clearTimeout(e),!a&&r||(r=await s.cacheMatch(t)),r}}},78757:function(e,t,n){n.d(t,{j:function(){return i}}),n(87524),n(70120);var s=n(3125),a=n(22118),r=n(50951);n(91094),n(76873);class i extends r._{constructor(e={}){super(e),this.plugins.some((e=>"cacheWillUpdate"in e))||this.plugins.unshift(a.S)}async _handle(e,t){const n=t.fetchAndCachePut(e).catch((()=>{}));t.waitUntil(n);let a,r=await t.cacheMatch(e);if(r);else try{r=await n}catch(e){e instanceof Error&&(a=e)}if(!r)throw new s.V("no-response",{url:e.url,error:a});return r}}},50951:function(e,t,n){n.d(t,{_:function(){return i}});var s=n(92536),a=n(3125),r=(n(70120),n(33119),n(76358));n(76873);class i{constructor(e={}){this.cacheName=s.x.getRuntimeName(e.cacheName),this.plugins=e.plugins||[],this.fetchOptions=e.fetchOptions,this.matchOptions=e.matchOptions}handle(e){const[t]=this.handleAll(e);return t}handleAll(e){e instanceof FetchEvent&&(e={event:e,request:e.request});const t=e.event,n="string"==typeof e.request?new Request(e.request):e.request,s="params"in e?e.params:void 0,a=new r.G(this,{event:t,request:n,params:s}),i=this._getResponse(a,n,t);return[i,this._awaitComplete(i,a,n,t)]}async _getResponse(e,t,n){let s;await e.runCallbacks("handlerWillStart",{event:n,request:t});try{if(s=await this._handle(t,e),!s||"error"===s.type)throw new a.V("no-response",{url:t.url})}catch(a){if(a instanceof Error)for(const r of e.iterateCallbacks("handlerDidError"))if(s=await r({error:a,event:n,request:t}),s)break;if(!s)throw a}for(const a of e.iterateCallbacks("handlerWillRespond"))s=await a({event:n,request:t,response:s});return s}async _awaitComplete(e,t,n,s){let a,r;try{a=await e}catch(r){}try{await t.runCallbacks("handlerDidRespond",{event:s,request:n,response:a}),await t.doneWaiting()}catch(e){e instanceof Error&&(r=e)}if(await t.runCallbacks("handlerDidComplete",{event:s,request:n,response:a,error:r}),t.destroy(),r)throw r}}},76358:function(e,t,n){function s(e,t){const n=new URL(e);for(const e of t)n.searchParams.delete(e);return n.href}n.d(t,{G:function(){return h}}),n(87524),n(10913);class a{constructor(){this.promise=new Promise(((e,t)=>{this.resolve=e,this.reject=t}))}}n(70120);var r=n(87565),i=n(33119),o=n(16902),c=n(3125);function u(e){return"string"==typeof e?new Request(e):e}n(76873);class h{constructor(e,t){this._cacheKeys={},Object.assign(this,t),this.event=t.event,this._strategy=e,this._handlerDeferred=new a,this._extendLifetimePromises=[],this._plugins=[...e.plugins],this._pluginStateMap=new Map;for(const e of this._plugins)this._pluginStateMap.set(e,{});this.event.waitUntil(this._handlerDeferred.promise)}async fetch(e){const{event:t}=this;let n=u(e);if("navigate"===n.mode&&t instanceof FetchEvent&&t.preloadResponse){const e=await t.preloadResponse;if(e)return e}const s=this.hasCallback("fetchDidFail")?n.clone():null;try{for(const e of this.iterateCallbacks("requestWillFetch"))n=await e({request:n.clone(),event:t})}catch(e){if(e instanceof Error)throw new c.V("plugin-error-request-will-fetch",{thrownErrorMessage:e.message})}const a=n.clone();try{let e;e=await fetch(n,"navigate"===n.mode?void 0:this._strategy.fetchOptions);for(const n of this.iterateCallbacks("fetchDidSucceed"))e=await n({event:t,request:a,response:e});return e}catch(e){throw s&&await this.runCallbacks("fetchDidFail",{error:e,event:t,originalRequest:s.clone(),request:a.clone()}),e}}async fetchAndCachePut(e){const t=await this.fetch(e),n=t.clone();return this.waitUntil(this.cachePut(e,n)),t}async cacheMatch(e){const t=u(e);let n;const{cacheName:s,matchOptions:a}=this._strategy,r=await this.getCacheKey(t,"read"),i=Object.assign(Object.assign({},a),{cacheName:s});n=await caches.match(r,i);for(const e of this.iterateCallbacks("cachedResponseWillBeUsed"))n=await e({cacheName:s,matchOptions:a,cachedResponse:n,request:r,event:this.event})||void 0;return n}async cachePut(e,t){const n=u(e);await(0,o.V)(0);const a=await this.getCacheKey(n,"write");if(!t)throw new c.V("cache-put-with-no-response",{url:(0,i.C)(a.url)});const h=await this._ensureResponseSafeToCache(t);if(!h)return!1;const{cacheName:l,matchOptions:d}=this._strategy,f=await self.caches.open(l),p=this.hasCallback("cacheDidUpdate"),g=p?await async function(e,t,n,a){const r=s(t.url,n);if(t.url===r)return e.match(t,a);const i=Object.assign(Object.assign({},a),{ignoreSearch:!0}),o=await e.keys(t,i);for(const t of o)if(r===s(t.url,n))return e.match(t,a)}(f,a.clone(),["__WB_REVISION__"],d):null;try{await f.put(a,p?h.clone():h)}catch(e){if(e instanceof Error)throw"QuotaExceededError"===e.name&&await async function(){for(const e of r.f)await e()}(),e}for(const e of this.iterateCallbacks("cacheDidUpdate"))await e({cacheName:l,oldResponse:g,newResponse:h.clone(),request:a,event:this.event});return!0}async getCacheKey(e,t){const n=`${e.url} | ${t}`;if(!this._cacheKeys[n]){let s=e;for(const e of this.iterateCallbacks("cacheKeyWillBeUsed"))s=u(await e({mode:t,request:s,event:this.event,params:this.params}));this._cacheKeys[n]=s}return this._cacheKeys[n]}hasCallback(e){for(const t of this._strategy.plugins)if(e in t)return!0;return!1}async runCallbacks(e,t){for(const n of this.iterateCallbacks(e))await n(t)}*iterateCallbacks(e){for(const t of this._strategy.plugins)if("function"==typeof t[e]){const n=this._pluginStateMap.get(t),s=s=>{const a=Object.assign(Object.assign({},s),{state:n});return t[e](a)};yield s}}waitUntil(e){return this._extendLifetimePromises.push(e),e}async doneWaiting(){let e;for(;e=this._extendLifetimePromises.shift();)await e}destroy(){this._handlerDeferred.resolve(null)}async _ensureResponseSafeToCache(e){let t=e,n=!1;for(const e of this.iterateCallbacks("cacheWillUpdate"))if(t=await e({request:this.request,response:t,event:this.event})||void 0,n=!0,!t)break;return n||t&&200!==t.status&&(t=void 0),t}}},76873:function(){try{self["workbox:strategies:6.5.2"]&&_()}catch(e){}},22118:function(e,t,n){n.d(t,{S:function(){return s}}),n(76873);const s={cacheWillUpdate:async({response:e})=>200===e.status||0===e.status?e:null}},91094:function(e,t,n){n(70120),n(33119),n(76873)},99819:function(e,t,n){n.r(t),n.d(t,{CacheableResponse:function(){return s.v},CacheableResponsePlugin:function(){return a.x}});var s=n(35414),a=n(13709);n(94895)},54065:function(e,t,n){n.r(t),n.d(t,{CacheExpiration:function(){return s.p},ExpirationPlugin:function(){return a.Q}});var s=n(95400),a=n(9491);n(6550)},69522:function(e,t,n){n.r(t),n.d(t,{googleFontsCache:function(){return c},imageCache:function(){return h},offlineFallback:function(){return E},pageCache:function(){return f},staticResourceCache:function(){return l},warmStrategyCache:function(){return u}});var s=n(5917),a=n(78757),r=n(44868),i=n(13709),o=n(9491);function c(e={}){const t=`${e.cachePrefix||"google-fonts"}-stylesheets`,n=`${e.cachePrefix||"google-fonts"}-webfonts`,c=e.maxAgeSeconds||31536e3,u=e.maxEntries||30;(0,s.X)((({url:e})=>"https://fonts.googleapis.com"===e.origin),new a.j({cacheName:t})),(0,s.X)((({url:e})=>"https://fonts.gstatic.com"===e.origin),new r.b({cacheName:n,plugins:[new i.x({statuses:[0,200]}),new o.Q({maxAgeSeconds:c,maxEntries:u})]}))}function u(e){self.addEventListener("install",(t=>{const n=e.urls.map((n=>e.strategy.handleAll({event:t,request:new Request(n)})[1]));t.waitUntil(Promise.all(n))}))}function h(e={}){const t=e.cacheName||"images",n=e.matchCallback||(({request:e})=>"image"===e.destination),a=e.maxAgeSeconds||2592e3,c=e.maxEntries||60,h=e.plugins||[];h.push(new i.x({statuses:[0,200]})),h.push(new o.Q({maxEntries:c,maxAgeSeconds:a}));const l=new r.b({cacheName:t,plugins:h});(0,s.X)(n,l),e.warmCache&&u({urls:e.warmCache,strategy:l})}function l(e={}){const t=e.cacheName||"static-resources",n=e.matchCallback||(({request:e})=>"style"===e.destination||"script"===e.destination||"worker"===e.destination),r=e.plugins||[];r.push(new i.x({statuses:[0,200]}));const o=new a.j({cacheName:t,plugins:r});(0,s.X)(n,o),e.warmCache&&u({urls:e.warmCache,strategy:o})}n(9144);var d=n(70495);function f(e={}){const t=e.cacheName||"pages",n=e.matchCallback||(({request:e})=>"navigate"===e.mode),a=e.networkTimeoutSeconds||3,r=e.plugins||[];r.push(new i.x({statuses:[0,200]}));const o=new d.n({networkTimeoutSeconds:a,cacheName:t,plugins:r});(0,s.X)(n,o),e.warmCache&&u({urls:e.warmCache,strategy:o})}var p=n(96226),g=(n(87524),n(92536)),w=(n(70120),n(3125));function m(e,t){const n=t();return e.waitUntil(n),n}function y(e){if(!e)throw new w.V("add-to-cache-list-unexpected-type",{entry:e});if("string"==typeof e){const t=new URL(e,location.href);return{cacheKey:t.href,url:t.href}}const{revision:t,url:n}=e;if(!n)throw new w.V("add-to-cache-list-unexpected-type",{entry:e});if(!t){const e=new URL(n,location.href);return{cacheKey:e.href,url:e.href}}const s=new URL(n,location.href),a=new URL(n,location.href);return s.searchParams.set("__WB_REVISION__",t),{cacheKey:s.href,url:a.href}}n(10913),n(7977);class _{constructor(){this.updatedURLs=[],this.notUpdatedURLs=[],this.handlerWillStart=async({request:e,state:t})=>{t&&(t.originalRequest=e)},this.cachedResponseWillBeUsed=async({event:e,state:t,cachedResponse:n})=>{if("install"===e.type&&t&&t.originalRequest&&t.originalRequest instanceof Request){const e=t.originalRequest.url;n?this.notUpdatedURLs.push(e):this.updatedURLs.push(e)}return n}}}class v{constructor({precacheController:e}){this.cacheKeyWillBeUsed=async({request:e,params:t})=>{const n=(null==t?void 0:t.cacheKey)||this._precacheController.getCacheKeyForURL(e.url);return n?new Request(n,{headers:e.headers}):e},this._precacheController=e}}let b;n(33119);var R=n(50951);class x extends R._{constructor(e={}){e.cacheName=g.x.getPrecacheName(e.cacheName),super(e),this._fallbackToNetwork=!1!==e.fallbackToNetwork,this.plugins.push(x.copyRedirectedCacheableResponsesPlugin)}async _handle(e,t){return await t.cacheMatch(e)||(t.event&&"install"===t.event.type?await this._handleInstall(e,t):await this._handleFetch(e,t))}async _handleFetch(e,t){let n;const s=t.params||{};if(!this._fallbackToNetwork)throw new w.V("missing-precache-entry",{cacheName:this.cacheName,url:e.url});{const a=s.integrity,r=e.integrity,i=!r||r===a;n=await t.fetch(new Request(e,{integrity:r||a})),a&&i&&(this._useDefaultCacheabilityPluginIfNeeded(),await t.cachePut(e,n.clone()))}return n}async _handleInstall(e,t){this._useDefaultCacheabilityPluginIfNeeded();const n=await t.fetch(e);if(!await t.cachePut(e,n.clone()))throw new w.V("bad-precaching-response",{url:e.url,status:n.status});return n}_useDefaultCacheabilityPluginIfNeeded(){let e=null,t=0;for(const[n,s]of this.plugins.entries())s!==x.copyRedirectedCacheableResponsesPlugin&&(s===x.defaultPrecacheCacheabilityPlugin&&(e=n),s.cacheWillUpdate&&t++);0===t?this.plugins.push(x.defaultPrecacheCacheabilityPlugin):t>1&&null!==e&&this.plugins.splice(e,1)}}x.defaultPrecacheCacheabilityPlugin={cacheWillUpdate:async({response:e})=>!e||e.status>=400?null:e},x.copyRedirectedCacheableResponsesPlugin={cacheWillUpdate:async({response:e})=>e.redirected?await async function(e,t){let n=null;if(e.url&&(n=new URL(e.url).origin),n!==self.location.origin)throw new w.V("cross-origin-copy-response",{origin:n});const s=e.clone(),a={headers:new Headers(s.headers),status:s.status,statusText:s.statusText},r=t?t(a):a,i=function(){if(void 0===b){const e=new Response("");if("body"in e)try{new Response(e.body),b=!0}catch(e){b=!1}b=!1}return b}()?s.body:await s.blob();return new Response(i,r)}(e):e};class C{constructor({cacheName:e,plugins:t=[],fallbackToNetwork:n=!0}={}){this._urlsToCacheKeys=new Map,this._urlsToCacheModes=new Map,this._cacheKeysToIntegrities=new Map,this._strategy=new x({cacheName:g.x.getPrecacheName(e),plugins:[...t,new v({precacheController:this})],fallbackToNetwork:n}),this.install=this.install.bind(this),this.activate=this.activate.bind(this)}get strategy(){return this._strategy}precache(e){this.addToCacheList(e),this._installAndActiveListenersAdded||(self.addEventListener("install",this.install),self.addEventListener("activate",this.activate),this._installAndActiveListenersAdded=!0)}addToCacheList(e){const t=[];for(const n of e){"string"==typeof n?t.push(n):n&&void 0===n.revision&&t.push(n.url);const{cacheKey:e,url:s}=y(n),a="string"!=typeof n&&n.revision?"reload":"default";if(this._urlsToCacheKeys.has(s)&&this._urlsToCacheKeys.get(s)!==e)throw new w.V("add-to-cache-list-conflicting-entries",{firstEntry:this._urlsToCacheKeys.get(s),secondEntry:e});if("string"!=typeof n&&n.integrity){if(this._cacheKeysToIntegrities.has(e)&&this._cacheKeysToIntegrities.get(e)!==n.integrity)throw new w.V("add-to-cache-list-conflicting-integrities",{url:s});this._cacheKeysToIntegrities.set(e,n.integrity)}if(this._urlsToCacheKeys.set(s,e),this._urlsToCacheModes.set(s,a),t.length>0){const e=`Workbox is precaching URLs without revision info: ${t.join(", ")}\nThis is generally NOT safe. Learn more at https://bit.ly/wb-precache`;console.warn(e)}}}install(e){return m(e,(async()=>{const t=new _;this.strategy.plugins.push(t);for(const[t,n]of this._urlsToCacheKeys){const s=this._cacheKeysToIntegrities.get(n),a=this._urlsToCacheModes.get(t),r=new Request(t,{integrity:s,cache:a,credentials:"same-origin"});await Promise.all(this.strategy.handleAll({params:{cacheKey:n},request:r,event:e}))}const{updatedURLs:n,notUpdatedURLs:s}=t;return{updatedURLs:n,notUpdatedURLs:s}}))}activate(e){return m(e,(async()=>{const e=await self.caches.open(this.strategy.cacheName),t=await e.keys(),n=new Set(this._urlsToCacheKeys.values()),s=[];for(const a of t)n.has(a.url)||(await e.delete(a),s.push(a.url));return{deletedURLs:s}}))}getURLsToCacheKeys(){return this._urlsToCacheKeys}getCachedURLs(){return[...this._urlsToCacheKeys.keys()]}getCacheKeyForURL(e){const t=new URL(e,location.href);return this._urlsToCacheKeys.get(t.href)}getIntegrityForCacheKey(e){return this._cacheKeysToIntegrities.get(e)}async matchPrecache(e){const t=e instanceof Request?e.url:e,n=this.getCacheKeyForURL(t);if(n)return(await self.caches.open(this.strategy.cacheName)).match(n)}createHandlerBoundToURL(e){const t=this.getCacheKeyForURL(e);if(!t)throw new w.V("non-precached-url",{url:e});return n=>(n.request=new Request(e),n.params=Object.assign({cacheKey:t},n.params),this.strategy.handle(n))}}let k;function q(e){return(k||(k=new C),k).matchPrecache(e)}function E(e={}){const t=e.pageFallback||"offline.html",n=e.imageFallback||!1,s=e.fontFallback||!1;self.addEventListener("install",(e=>{const a=[t];n&&a.push(n),s&&a.push(s),e.waitUntil(self.caches.open("workbox-offline-fallbacks").then((e=>e.addAll(a))))})),(0,p.H)((async e=>{const a=e.request.destination,r=await self.caches.open("workbox-offline-fallbacks");return"document"===a?await q(t)||await r.match(t)||Response.error():"image"===a&&!1!==n?await q(n)||await r.match(n)||Response.error():"font"===a&&!1!==s&&(await q(s)||await r.match(s))||Response.error()}))}},44615:function(e,t,n){n.r(t),n.d(t,{NavigationRoute:function(){return a},RegExpRoute:function(){return r.t},Route:function(){return s.A},Router:function(){return o.F},registerRoute:function(){return i.X},setCatchHandler:function(){return c.H},setDefaultHandler:function(){return h}}),n(87524),n(70120);var s=n(95188);n(39080);class a extends s.A{constructor(e,{allowlist:t=[/./],denylist:n=[]}={}){super((e=>this._match(e)),e),this._allowlist=t,this._denylist=n}_match({url:e,request:t}){if(t&&"navigate"!==t.mode)return!1;const n=e.pathname+e.search;for(const e of this._denylist)if(e.test(n))return!1;return!!this._allowlist.some((e=>e.test(n)))}}var r=n(74989),i=n(5917),o=n(71491),c=n(96226),u=n(63486);function h(e){(0,u.u)().setDefaultHandler(e)}},67162:function(e,t,n){n.r(t),n.d(t,{CacheFirst:function(){return s.b},CacheOnly:function(){return i},NetworkFirst:function(){return o.n},NetworkOnly:function(){return u},StaleWhileRevalidate:function(){return h.j},Strategy:function(){return r._},StrategyHandler:function(){return l.G}});var s=n(44868),a=(n(87524),n(70120),n(3125)),r=n(50951);n(91094),n(76873);class i extends r._{async _handle(e,t){const n=await t.cacheMatch(e);if(!n)throw new a.V("no-response",{url:e.url});return n}}var o=n(70495),c=n(16902);class u extends r._{constructor(e={}){super(e),this._networkTimeoutSeconds=e.networkTimeoutSeconds||0}async _handle(e,t){let n,s;try{const n=[t.fetch(e)];if(this._networkTimeoutSeconds){const e=(0,c.V)(1e3*this._networkTimeoutSeconds);n.push(e)}if(s=await Promise.race(n),!s)throw new Error(`Timed out the network response after ${this._networkTimeoutSeconds} seconds.`)}catch(e){e instanceof Error&&(n=e)}if(!s)throw new a.V("no-response",{url:e.url,error:n});return s}}var h=n(78757),l=n(76358)}},t={};function n(s){var a=t[s];if(void 0!==a)return a.exports;var r=t[s]={exports:{}};return e[s].call(r.exports,r,r.exports,n),r.exports}n.n=function(e){var t=e&&e.__esModule?function(){return e.default}:function(){return e};return n.d(t,{a:t}),t},n.d=function(e,t){for(var s in t)n.o(t,s)&&!n.o(e,s)&&Object.defineProperty(e,s,{enumerable:!0,get:t[s]})},n.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},n.r=function(e){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},n(37145)}();