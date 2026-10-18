/* Generated at build time; CSP-safe, no runtime schema compiler. */
var __getOwnPropNames = Object.getOwnPropertyNames;
var __commonJS = (cb, mod) =>
  function __require() {
    return (
      mod ||
        (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod),
      mod.exports
    );
  };

// node_modules/ajv/dist/runtime/ucs2length.js
var require_ucs2length = __commonJS({
  "node_modules/ajv/dist/runtime/ucs2length.js"(exports) {
    "use strict";
    Object.defineProperty(exports, "__esModule", { value: true });
    function ucs2length(str) {
      const len = str.length;
      let length = 0;
      let pos = 0;
      let value;
      while (pos < len) {
        length++;
        value = str.charCodeAt(pos++);
        if (value >= 55296 && value <= 56319 && pos < len) {
          value = str.charCodeAt(pos);
          if ((value & 64512) === 56320) pos++;
        }
      }
      return length;
    }
    exports.default = ucs2length;
    ucs2length.code = 'require("ajv/dist/runtime/ucs2length").default';
  },
});

// node_modules/ajv-formats/dist/formats.js
var require_formats = __commonJS({
  "node_modules/ajv-formats/dist/formats.js"(exports) {
    "use strict";
    Object.defineProperty(exports, "__esModule", { value: true });
    exports.formatNames = exports.fastFormats = exports.fullFormats = void 0;
    function fmtDef(validate, compare) {
      return { validate, compare };
    }
    exports.fullFormats = {
      // date: http://tools.ietf.org/html/rfc3339#section-5.6
      date: fmtDef(date, compareDate),
      // date-time: http://tools.ietf.org/html/rfc3339#section-5.6
      time: fmtDef(getTime(true), compareTime),
      "date-time": fmtDef(getDateTime(true), compareDateTime),
      "iso-time": fmtDef(getTime(), compareIsoTime),
      "iso-date-time": fmtDef(getDateTime(), compareIsoDateTime),
      // duration: https://tools.ietf.org/html/rfc3339#appendix-A
      duration:
        /^P(?!$)((\d+Y)?(\d+M)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+S)?)?|(\d+W)?)$/,
      uri,
      "uri-reference":
        /^(?:[a-z][a-z0-9+\-.]*:)?(?:\/?\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:]|%[0-9a-f]{2})*@)?(?:\[(?:(?:(?:(?:[0-9a-f]{1,4}:){6}|::(?:[0-9a-f]{1,4}:){5}|(?:[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){4}|(?:(?:[0-9a-f]{1,4}:){0,1}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){3}|(?:(?:[0-9a-f]{1,4}:){0,2}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){2}|(?:(?:[0-9a-f]{1,4}:){0,3}[0-9a-f]{1,4})?::[0-9a-f]{1,4}:|(?:(?:[0-9a-f]{1,4}:){0,4}[0-9a-f]{1,4})?::)(?:[0-9a-f]{1,4}:[0-9a-f]{1,4}|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?))|(?:(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4})?::[0-9a-f]{1,4}|(?:(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4})?::)|[Vv][0-9a-f]+\.[a-z0-9\-._~!$&'()*+,;=:]+)\]|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)|(?:[a-z0-9\-._~!$&'"()*+,;=]|%[0-9a-f]{2})*)(?::\d*)?(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*|\/(?:(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*)?|(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'"()*+,;=:@]|%[0-9a-f]{2})*)*)?(?:\?(?:[a-z0-9\-._~!$&'"()*+,;=:@/?]|%[0-9a-f]{2})*)?(?:#(?:[a-z0-9\-._~!$&'"()*+,;=:@/?]|%[0-9a-f]{2})*)?$/i,
      // uri-template: https://tools.ietf.org/html/rfc6570
      "uri-template":
        /^(?:(?:[^\x00-\x20"'<>%\\^`{|}]|%[0-9a-f]{2})|\{[+#./;?&=,!@|]?(?:[a-z0-9_]|%[0-9a-f]{2})+(?::[1-9][0-9]{0,3}|\*)?(?:,(?:[a-z0-9_]|%[0-9a-f]{2})+(?::[1-9][0-9]{0,3}|\*)?)*\})*$/i,
      // For the source: https://gist.github.com/dperini/729294
      // For test cases: https://mathiasbynens.be/demo/url-regex
      url: /^(?:https?|ftp):\/\/(?:\S+(?::\S*)?@)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z0-9\u{00a1}-\u{ffff}]+-)*[a-z0-9\u{00a1}-\u{ffff}]+)(?:\.(?:[a-z0-9\u{00a1}-\u{ffff}]+-)*[a-z0-9\u{00a1}-\u{ffff}]+)*(?:\.(?:[a-z\u{00a1}-\u{ffff}]{2,})))(?::\d{2,5})?(?:\/[^\s]*)?$/iu,
      email:
        /^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i,
      hostname:
        /^(?=.{1,253}\.?$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[-0-9a-z]{0,61}[0-9a-z])?)*\.?$/i,
      // optimized https://www.safaribooksonline.com/library/view/regular-expressions-cookbook/9780596802837/ch07s16.html
      ipv4: /^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$/,
      ipv6: /^((([0-9a-f]{1,4}:){7}([0-9a-f]{1,4}|:))|(([0-9a-f]{1,4}:){6}(:[0-9a-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9a-f]{1,4}:){5}(((:[0-9a-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9a-f]{1,4}:){4}(((:[0-9a-f]{1,4}){1,3})|((:[0-9a-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){3}(((:[0-9a-f]{1,4}){1,4})|((:[0-9a-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){2}(((:[0-9a-f]{1,4}){1,5})|((:[0-9a-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9a-f]{1,4}:){1}(((:[0-9a-f]{1,4}){1,6})|((:[0-9a-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9a-f]{1,4}){1,7})|((:[0-9a-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))$/i,
      regex,
      // uuid: http://tools.ietf.org/html/rfc4122
      uuid: /^(?:urn:uuid:)?[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i,
      // JSON-pointer: https://tools.ietf.org/html/rfc6901
      // uri fragment: https://tools.ietf.org/html/rfc3986#appendix-A
      "json-pointer": /^(?:\/(?:[^~/]|~0|~1)*)*$/,
      "json-pointer-uri-fragment":
        /^#(?:\/(?:[a-z0-9_\-.!$&'()*+,;:=@]|%[0-9a-f]{2}|~0|~1)*)*$/i,
      // relative JSON-pointer: http://tools.ietf.org/html/draft-luff-relative-json-pointer-00
      "relative-json-pointer":
        /^(?:0|[1-9][0-9]*)(?:#|(?:\/(?:[^~/]|~0|~1)*)*)$/,
      // the following formats are used by the openapi specification: https://spec.openapis.org/oas/v3.0.0#data-types
      // byte: https://github.com/miguelmota/is-base64
      byte,
      // signed 32 bit integer
      int32: { type: "number", validate: validateInt32 },
      // signed 64 bit integer
      int64: { type: "number", validate: validateInt64 },
      // C-type float
      float: { type: "number", validate: validateNumber },
      // C-type double
      double: { type: "number", validate: validateNumber },
      // hint to the UI to hide input strings
      password: true,
      // unchecked string payload
      binary: true,
    };
    exports.fastFormats = {
      ...exports.fullFormats,
      date: fmtDef(/^\d\d\d\d-[0-1]\d-[0-3]\d$/, compareDate),
      time: fmtDef(
        /^(?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)$/i,
        compareTime,
      ),
      "date-time": fmtDef(
        /^\d\d\d\d-[0-1]\d-[0-3]\dt(?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)$/i,
        compareDateTime,
      ),
      "iso-time": fmtDef(
        /^(?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)?$/i,
        compareIsoTime,
      ),
      "iso-date-time": fmtDef(
        /^\d\d\d\d-[0-1]\d-[0-3]\d[t\s](?:[0-2]\d:[0-5]\d:[0-5]\d|23:59:60)(?:\.\d+)?(?:z|[+-]\d\d(?::?\d\d)?)?$/i,
        compareIsoDateTime,
      ),
      // uri: https://github.com/mafintosh/is-my-json-valid/blob/master/formats.js
      uri: /^(?:[a-z][a-z0-9+\-.]*:)(?:\/?\/)?[^\s]*$/i,
      "uri-reference":
        /^(?:(?:[a-z][a-z0-9+\-.]*:)?\/?\/)?(?:[^\\\s#][^\s#]*)?(?:#[^\\\s]*)?$/i,
      // email (sources from jsen validator):
      // http://stackoverflow.com/questions/201323/using-a-regular-expression-to-validate-an-email-address#answer-8829363
      // http://www.w3.org/TR/html5/forms.html#valid-e-mail-address (search for 'wilful violation')
      email:
        /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$/i,
    };
    exports.formatNames = Object.keys(exports.fullFormats);
    function isLeapYear(year) {
      return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    }
    var DATE = /^(\d\d\d\d)-(\d\d)-(\d\d)$/;
    var DAYS = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    function date(str) {
      const matches = DATE.exec(str);
      if (!matches) return false;
      const year = +matches[1];
      const month = +matches[2];
      const day = +matches[3];
      return (
        month >= 1 &&
        month <= 12 &&
        day >= 1 &&
        day <= (month === 2 && isLeapYear(year) ? 29 : DAYS[month])
      );
    }
    function compareDate(d1, d2) {
      if (!(d1 && d2)) return void 0;
      if (d1 > d2) return 1;
      if (d1 < d2) return -1;
      return 0;
    }
    var TIME =
      /^(\d\d):(\d\d):(\d\d(?:\.\d+)?)(z|([+-])(\d\d)(?::?(\d\d))?)?$/i;
    function getTime(strictTimeZone) {
      return function time(str) {
        const matches = TIME.exec(str);
        if (!matches) return false;
        const hr = +matches[1];
        const min = +matches[2];
        const sec = +matches[3];
        const tz = matches[4];
        const tzSign = matches[5] === "-" ? -1 : 1;
        const tzH = +(matches[6] || 0);
        const tzM = +(matches[7] || 0);
        if (tzH > 23 || tzM > 59 || (strictTimeZone && !tz)) return false;
        if (hr <= 23 && min <= 59 && sec < 60) return true;
        const utcMin = min - tzM * tzSign;
        const utcHr = hr - tzH * tzSign - (utcMin < 0 ? 1 : 0);
        return (
          (utcHr === 23 || utcHr === -1) &&
          (utcMin === 59 || utcMin === -1) &&
          sec < 61
        );
      };
    }
    function compareTime(s1, s2) {
      if (!(s1 && s2)) return void 0;
      const t1 = /* @__PURE__ */ new Date("2020-01-01T" + s1).valueOf();
      const t2 = /* @__PURE__ */ new Date("2020-01-01T" + s2).valueOf();
      if (!(t1 && t2)) return void 0;
      return t1 - t2;
    }
    function compareIsoTime(t1, t2) {
      if (!(t1 && t2)) return void 0;
      const a1 = TIME.exec(t1);
      const a2 = TIME.exec(t2);
      if (!(a1 && a2)) return void 0;
      t1 = a1[1] + a1[2] + a1[3];
      t2 = a2[1] + a2[2] + a2[3];
      if (t1 > t2) return 1;
      if (t1 < t2) return -1;
      return 0;
    }
    var DATE_TIME_SEPARATOR = /t|\s/i;
    function getDateTime(strictTimeZone) {
      const time = getTime(strictTimeZone);
      return function date_time(str) {
        const dateTime = str.split(DATE_TIME_SEPARATOR);
        return dateTime.length === 2 && date(dateTime[0]) && time(dateTime[1]);
      };
    }
    function compareDateTime(dt1, dt2) {
      if (!(dt1 && dt2)) return void 0;
      const d1 = new Date(dt1).valueOf();
      const d2 = new Date(dt2).valueOf();
      if (!(d1 && d2)) return void 0;
      return d1 - d2;
    }
    function compareIsoDateTime(dt1, dt2) {
      if (!(dt1 && dt2)) return void 0;
      const [d1, t1] = dt1.split(DATE_TIME_SEPARATOR);
      const [d2, t2] = dt2.split(DATE_TIME_SEPARATOR);
      const res = compareDate(d1, d2);
      if (res === void 0) return void 0;
      return res || compareTime(t1, t2);
    }
    var NOT_URI_FRAGMENT = /\/|:/;
    var URI =
      /^(?:[a-z][a-z0-9+\-.]*:)(?:\/?\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:]|%[0-9a-f]{2})*@)?(?:\[(?:(?:(?:(?:[0-9a-f]{1,4}:){6}|::(?:[0-9a-f]{1,4}:){5}|(?:[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){4}|(?:(?:[0-9a-f]{1,4}:){0,1}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){3}|(?:(?:[0-9a-f]{1,4}:){0,2}[0-9a-f]{1,4})?::(?:[0-9a-f]{1,4}:){2}|(?:(?:[0-9a-f]{1,4}:){0,3}[0-9a-f]{1,4})?::[0-9a-f]{1,4}:|(?:(?:[0-9a-f]{1,4}:){0,4}[0-9a-f]{1,4})?::)(?:[0-9a-f]{1,4}:[0-9a-f]{1,4}|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?))|(?:(?:[0-9a-f]{1,4}:){0,5}[0-9a-f]{1,4})?::[0-9a-f]{1,4}|(?:(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{1,4})?::)|[Vv][0-9a-f]+\.[a-z0-9\-._~!$&'()*+,;=:]+)\]|(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)|(?:[a-z0-9\-._~!$&'()*+,;=]|%[0-9a-f]{2})*)(?::\d*)?(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*|\/(?:(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*)?|(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})+(?:\/(?:[a-z0-9\-._~!$&'()*+,;=:@]|%[0-9a-f]{2})*)*)(?:\?(?:[a-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9a-f]{2})*)?(?:#(?:[a-z0-9\-._~!$&'()*+,;=:@/?]|%[0-9a-f]{2})*)?$/i;
    function uri(str) {
      return NOT_URI_FRAGMENT.test(str) && URI.test(str);
    }
    var BYTE =
      /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/gm;
    function byte(str) {
      BYTE.lastIndex = 0;
      return BYTE.test(str);
    }
    var MIN_INT32 = -(2 ** 31);
    var MAX_INT32 = 2 ** 31 - 1;
    function validateInt32(value) {
      return (
        Number.isInteger(value) && value <= MAX_INT32 && value >= MIN_INT32
      );
    }
    function validateInt64(value) {
      return Number.isInteger(value);
    }
    function validateNumber() {
      return true;
    }
    var Z_ANCHOR = /[^\\]\\Z/;
    function regex(str) {
      if (Z_ANCHOR.test(str)) return false;
      try {
        new RegExp(str);
        return true;
      } catch (e) {
        return false;
      }
    }
  },
});

// browser-validator.cjs
var require_browser_validator = __commonJS({
  "browser-validator.cjs"(exports, module) {
    module.exports = validate20;
    module.exports.default = validate20;
    var schema31 = {
      $defs: {
        AlarmDeliverySnapshot: {
          properties: {
            alarms: {
              items: { $ref: "#/$defs/AlarmDeliveryState" },
              title: "Alarms",
              type: "array",
            },
            available: { default: false, title: "Available", type: "boolean" },
          },
          title: "AlarmDeliverySnapshot",
          type: "object",
        },
        AlarmDeliveryState: {
          additionalProperties: false,
          properties: {
            alarm_id: { format: "uuid", title: "Alarm Id", type: "string" },
            delivery_status: {
              enum: [
                "pending",
                "delivered",
                "started",
                "completed",
                "cancelled",
                "failed",
                "indeterminate",
              ],
              title: "Delivery Status",
              type: "string",
            },
            device_id: {
              maxLength: 64,
              minLength: 1,
              pattern: "^[a-zA-Z0-9_-]+$",
              title: "Device Id",
              type: "string",
            },
            pending: { title: "Pending", type: "boolean" },
            updated_at: {
              anyOf: [
                { format: "date-time", type: "string" },
                { type: "null" },
              ],
              title: "Updated At",
            },
          },
          required: [
            "alarm_id",
            "device_id",
            "delivery_status",
            "updated_at",
            "pending",
          ],
          title: "AlarmDeliveryState",
          type: "object",
        },
        AlarmRecord: {
          additionalProperties: false,
          properties: {
            alarm_id: { format: "uuid", title: "Alarm Id", type: "string" },
            device_id: {
              maxLength: 64,
              minLength: 1,
              pattern: "^[a-zA-Z0-9_-]+$",
              title: "Device Id",
              type: "string",
            },
            expired_at: {
              format: "date-time",
              title: "Expired At",
              type: "string",
            },
            timer_id: { format: "uuid", title: "Timer Id", type: "string" },
          },
          required: ["alarm_id", "timer_id", "device_id", "expired_at"],
          title: "AlarmRecord",
          type: "object",
        },
        ApplicationSnapshot: {
          additionalProperties: false,
          properties: {
            alarms: {
              items: { $ref: "#/$defs/AlarmRecord" },
              title: "Alarms",
              type: "array",
            },
            availability: {
              additionalProperties: true,
              title: "Availability",
              type: "object",
            },
            devices: {
              items: { additionalProperties: true, type: "object" },
              title: "Devices",
              type: "array",
            },
            revision: { minimum: 0, title: "Revision", type: "integer" },
            timers: {
              items: { $ref: "#/$defs/TimerRecord" },
              title: "Timers",
              type: "array",
            },
            timestamp: {
              format: "date-time",
              title: "Timestamp",
              type: "string",
            },
            tools: {
              items: { additionalProperties: true, type: "object" },
              title: "Tools",
              type: "array",
            },
            version: {
              const: 1,
              default: 1,
              title: "Version",
              type: "integer",
            },
            views: {
              items: { additionalProperties: true, type: "object" },
              title: "Views",
              type: "array",
            },
            weather: {
              items: { $ref: "#/$defs/Forecast" },
              title: "Weather",
              type: "array",
            },
          },
          required: ["timestamp", "revision"],
          title: "ApplicationSnapshot",
          type: "object",
        },
        BrowserGrant: {
          additionalProperties: false,
          properties: {
            captions: { default: false, title: "Captions", type: "boolean" },
            debug: { default: false, title: "Debug", type: "boolean" },
            home_control: {
              default: false,
              title: "Home Control",
              type: "boolean",
            },
            home_entities: {
              items: { type: "string" },
              title: "Home Entities",
              type: "array",
              uniqueItems: true,
            },
            timers: { default: false, title: "Timers", type: "boolean" },
            voice_control: {
              default: false,
              title: "Voice Control",
              type: "boolean",
            },
          },
          title: "BrowserGrant",
          type: "object",
        },
        BrowserHome: {
          additionalProperties: false,
          properties: {
            attributes: {
              additionalProperties: true,
              title: "Attributes",
              type: "object",
            },
            capabilities: {
              items: { type: "string" },
              title: "Capabilities",
              type: "array",
            },
            entity_id: { title: "Entity Id", type: "string" },
            last_updated: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Last Updated",
            },
            name: { maxLength: 160, title: "Name", type: "string" },
            observed_at: {
              format: "date-time",
              title: "Observed At",
              type: "string",
            },
            power_off: { title: "Power Off", type: "boolean" },
            power_on: { title: "Power On", type: "boolean" },
            remote_commands: {
              items: { type: "string" },
              title: "Remote Commands",
              type: "array",
            },
            source: {
              const: "home-assistant",
              title: "Source",
              type: "string",
            },
            state: { maxLength: 160, title: "State", type: "string" },
          },
          required: [
            "entity_id",
            "name",
            "state",
            "source",
            "observed_at",
            "last_updated",
            "attributes",
            "capabilities",
            "remote_commands",
            "power_on",
            "power_off",
          ],
          title: "BrowserHome",
          type: "object",
        },
        BrowserSession: {
          additionalProperties: false,
          properties: {
            csrf: { title: "Csrf", type: "string" },
            device_id: {
              maxLength: 64,
              minLength: 1,
              pattern: "^[a-zA-Z0-9_-]+$",
              title: "Device Id",
              type: "string",
            },
            expires_at: { title: "Expires At", type: "string" },
            id: { format: "uuid", title: "Id", type: "string" },
            name: { title: "Name", type: "string" },
            permissions: { $ref: "#/$defs/BrowserGrant" },
          },
          required: [
            "id",
            "device_id",
            "name",
            "expires_at",
            "csrf",
            "permissions",
          ],
          title: "BrowserSession",
          type: "object",
        },
        Current: {
          properties: {
            condition: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Condition",
            },
            feels_like: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "Feels Like",
            },
            humidity_pct: {
              anyOf: [
                { maximum: 100, minimum: 0, type: "number" },
                { type: "null" },
              ],
              title: "Humidity Pct",
            },
            kind: {
              const: "model_estimate",
              default: "model_estimate",
              title: "Kind",
              type: "string",
            },
            precipitation: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "Precipitation",
            },
            temperature: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "Temperature",
            },
            time: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Time",
            },
            wind_speed: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "Wind Speed",
            },
          },
          required: [
            "time",
            "temperature",
            "feels_like",
            "humidity_pct",
            "wind_speed",
            "condition",
            "precipitation",
          ],
          title: "Current",
          type: "object",
        },
        Day: {
          properties: {
            condition: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Condition",
            },
            date: { title: "Date", type: "string" },
            high: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "High",
            },
            kind: {
              const: "forecast",
              default: "forecast",
              title: "Kind",
              type: "string",
            },
            low: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "Low",
            },
            precipitation: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "Precipitation",
            },
            rain_probability_pct: {
              anyOf: [
                { maximum: 100, minimum: 0, type: "number" },
                { type: "null" },
              ],
              title: "Rain Probability Pct",
            },
            sunrise: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Sunrise",
            },
            sunset: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Sunset",
            },
          },
          required: [
            "date",
            "high",
            "low",
            "rain_probability_pct",
            "precipitation",
            "condition",
            "sunrise",
            "sunset",
          ],
          title: "Day",
          type: "object",
        },
        EdgeVoicePayload: {
          additionalProperties: false,
          properties: {
            error: {
              anyOf: [{ maxLength: 64, type: "string" }, { type: "null" }],
              default: null,
              title: "Error",
            },
            errors: {
              default: 0,
              minimum: 0,
              title: "Errors",
              type: "integer",
            },
            input_level_rms: {
              default: 0,
              maximum: 1,
              minimum: 0,
              title: "Input Level Rms",
              type: "number",
            },
            metrics: {
              additionalProperties: { type: "number" },
              maxProperties: 16,
              title: "Metrics",
              type: "object",
            },
            microphone: {
              default: false,
              title: "Microphone",
              type: "boolean",
            },
            muted: { default: true, title: "Muted", type: "boolean" },
            speaker: { default: false, title: "Speaker", type: "boolean" },
            state: {
              enum: [
                "STARTING",
                "IDLE",
                "WAKE_DETECTED",
                "LISTENING",
                "UPLOADING",
                "TRANSCRIBING",
                "THINKING",
                "TOOL_EXECUTING",
                "SYNTHESIZING",
                "DELIVERING",
                "SPEAKING",
                "FOLLOW_UP",
                "ERROR",
              ],
              title: "State",
              type: "string",
            },
            vad_ready: { default: false, title: "Vad Ready", type: "boolean" },
            wake_ready: {
              default: false,
              title: "Wake Ready",
              type: "boolean",
            },
          },
          required: ["state"],
          title: "EdgeVoicePayload",
          type: "object",
        },
        EventPage: {
          additionalProperties: false,
          properties: {
            cursor: { minimum: 0, title: "Cursor", type: "integer" },
            events: {
              items: { $ref: "#/$defs/SemanticEvent" },
              title: "Events",
              type: "array",
            },
            version: {
              const: 1,
              default: 1,
              title: "Version",
              type: "integer",
            },
          },
          required: ["cursor", "events"],
          title: "EventPage",
          type: "object",
        },
        Forecast: {
          properties: {
            cache_age_seconds: {
              default: 0,
              title: "Cache Age Seconds",
              type: "number",
            },
            current: { $ref: "#/$defs/Current" },
            daily: {
              items: { $ref: "#/$defs/Day" },
              title: "Daily",
              type: "array",
            },
            fetched_at: { title: "Fetched At", type: "string" },
            freshness_ttl_seconds: {
              default: 600,
              exclusiveMinimum: 0,
              title: "Freshness Ttl Seconds",
              type: "number",
            },
            hourly: {
              items: { $ref: "#/$defs/Hour" },
              title: "Hourly",
              type: "array",
            },
            location: { $ref: "#/$defs/Location" },
            measurement_units: {
              additionalProperties: { type: "string" },
              title: "Measurement Units",
              type: "object",
            },
            source: {
              const: "open-meteo",
              default: "open-meteo",
              title: "Source",
              type: "string",
            },
            source_age_seconds: {
              anyOf: [{ minimum: 0, type: "number" }, { type: "null" }],
              default: null,
              title: "Source Age Seconds",
            },
            source_timestamp: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Source Timestamp",
            },
            stale: { default: false, title: "Stale", type: "boolean" },
            units: {
              enum: ["imperial", "metric"],
              title: "Units",
              type: "string",
            },
            valid_from: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Valid From",
            },
            valid_until: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Valid Until",
            },
            version: {
              const: 1,
              default: 1,
              title: "Version",
              type: "integer",
            },
          },
          required: [
            "location",
            "units",
            "measurement_units",
            "current",
            "hourly",
            "daily",
            "fetched_at",
            "source_timestamp",
            "valid_from",
            "valid_until",
          ],
          title: "Forecast",
          type: "object",
        },
        Hour: {
          properties: {
            humidity_pct: {
              anyOf: [
                { maximum: 100, minimum: 0, type: "number" },
                { type: "null" },
              ],
              title: "Humidity Pct",
            },
            kind: {
              const: "forecast",
              default: "forecast",
              title: "Kind",
              type: "string",
            },
            precipitation: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "Precipitation",
            },
            rain_probability_pct: {
              anyOf: [
                { maximum: 100, minimum: 0, type: "number" },
                { type: "null" },
              ],
              title: "Rain Probability Pct",
            },
            temperature: {
              anyOf: [{ type: "number" }, { type: "null" }],
              title: "Temperature",
            },
            time: { title: "Time", type: "string" },
          },
          required: [
            "time",
            "temperature",
            "humidity_pct",
            "rain_probability_pct",
            "precipitation",
          ],
          title: "Hour",
          type: "object",
        },
        Location: {
          additionalProperties: false,
          properties: {
            latitude: {
              maximum: 90,
              minimum: -90,
              title: "Latitude",
              type: "number",
            },
            longitude: {
              maximum: 180,
              minimum: -180,
              title: "Longitude",
              type: "number",
            },
            name: {
              maxLength: 240,
              minLength: 1,
              title: "Name",
              type: "string",
            },
            timezone: { title: "Timezone", type: "string" },
          },
          required: ["name", "latitude", "longitude", "timezone"],
          title: "Location",
          type: "object",
        },
        SemanticEvent: {
          additionalProperties: false,
          properties: {
            device_id: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Device Id",
            },
            event_id: { title: "Event Id", type: "string" },
            payload: {
              additionalProperties: true,
              title: "Payload",
              type: "object",
            },
            resource_id: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Resource Id",
            },
            scope: { title: "Scope", type: "string" },
            sequence: { minimum: 1, title: "Sequence", type: "integer" },
            timestamp: {
              format: "date-time",
              title: "Timestamp",
              type: "string",
            },
            type: {
              enum: [
                "timer.created",
                "timer.updated",
                "timer.expired",
                "timer.acknowledged",
                "weather.updated",
                "home.entity_changed",
                "media.state_changed",
                "dashboard.show_view",
                "tool.execution_completed",
              ],
              title: "Type",
              type: "string",
            },
            version: {
              const: 1,
              default: 1,
              title: "Version",
              type: "integer",
            },
          },
          required: [
            "event_id",
            "timestamp",
            "sequence",
            "scope",
            "device_id",
            "type",
            "resource_id",
            "payload",
          ],
          title: "SemanticEvent",
          type: "object",
        },
        TimerRecord: {
          additionalProperties: false,
          properties: {
            acknowledged_at: {
              anyOf: [
                { format: "date-time", type: "string" },
                { type: "null" },
              ],
              title: "Acknowledged At",
            },
            created_at: {
              format: "date-time",
              title: "Created At",
              type: "string",
            },
            deadline: {
              anyOf: [
                { format: "date-time", type: "string" },
                { type: "null" },
              ],
              title: "Deadline",
            },
            device_id: {
              maxLength: 64,
              minLength: 1,
              pattern: "^[a-zA-Z0-9_-]+$",
              title: "Device Id",
              type: "string",
            },
            duration_ms: {
              exclusiveMinimum: 0,
              title: "Duration Ms",
              type: "integer",
            },
            expired_at: {
              anyOf: [
                { format: "date-time", type: "string" },
                { type: "null" },
              ],
              title: "Expired At",
            },
            id: { format: "uuid", title: "Id", type: "string" },
            name: {
              anyOf: [{ type: "string" }, { type: "null" }],
              title: "Name",
            },
            remaining_ms: {
              minimum: 0,
              title: "Remaining Ms",
              type: "integer",
            },
            status: {
              enum: [
                "RUNNING",
                "PAUSED",
                "EXPIRED",
                "CANCELLED",
                "ACKNOWLEDGED",
              ],
              title: "Status",
              type: "string",
            },
            updated_at: {
              format: "date-time",
              title: "Updated At",
              type: "string",
            },
            version: { minimum: 1, title: "Version", type: "integer" },
          },
          required: [
            "id",
            "device_id",
            "name",
            "duration_ms",
            "remaining_ms",
            "status",
            "created_at",
            "deadline",
            "expired_at",
            "acknowledged_at",
            "updated_at",
            "version",
          ],
          title: "TimerRecord",
          type: "object",
        },
        VoiceDeviceState: {
          additionalProperties: false,
          properties: {
            application: {
              anyOf: [
                { $ref: "#/$defs/ApplicationSnapshot" },
                { type: "null" },
              ],
              default: null,
            },
            connected: { default: false, title: "Connected", type: "boolean" },
            device_id: {
              maxLength: 64,
              minLength: 1,
              pattern: "^[a-zA-Z0-9_-]+$",
              title: "Device Id",
              type: "string",
            },
            edge: {
              anyOf: [{ $ref: "#/$defs/EdgeVoicePayload" }, { type: "null" }],
              default: null,
            },
            last_success: {
              anyOf: [
                { format: "date-time", type: "string" },
                { type: "null" },
              ],
              default: null,
              title: "Last Success",
            },
          },
          required: ["device_id"],
          title: "VoiceDeviceState",
          type: "object",
        },
        VoiceEvent: {
          additionalProperties: false,
          properties: {
            device_id: {
              maxLength: 64,
              minLength: 1,
              pattern: "^[a-zA-Z0-9_-]+$",
              title: "Device Id",
              type: "string",
            },
            event_id: { format: "uuid", title: "Event Id", type: "string" },
            payload: {
              additionalProperties: true,
              title: "Payload",
              type: "object",
            },
            revision: { minimum: 1, title: "Revision", type: "integer" },
            timestamp: {
              format: "date-time",
              title: "Timestamp",
              type: "string",
            },
            type: {
              enum: [
                "assistant.transcribing",
                "assistant.thinking",
                "assistant.tool_executing",
                "assistant.synthesizing",
                "assistant.delivering",
                "assistant.speaking",
                "assistant.follow_up",
                "assistant.error",
                "assistant.edge_state",
                "assistant.playback",
              ],
              title: "Type",
              type: "string",
            },
            version: { const: 1, title: "Version", type: "integer" },
          },
          required: [
            "version",
            "event_id",
            "revision",
            "timestamp",
            "device_id",
            "type",
            "payload",
          ],
          title: "VoiceEvent",
          type: "object",
        },
        VoiceSnapshot: {
          additionalProperties: false,
          properties: {
            alarm_delivery: { $ref: "#/$defs/AlarmDeliverySnapshot" },
            devices: {
              items: { $ref: "#/$defs/VoiceDeviceState" },
              title: "Devices",
              type: "array",
            },
            events: {
              items: { $ref: "#/$defs/VoiceEvent" },
              title: "Events",
              type: "array",
            },
            expires_after_seconds: {
              exclusiveMinimum: 0,
              title: "Expires After Seconds",
              type: "number",
            },
            resync_required: {
              default: false,
              title: "Resync Required",
              type: "boolean",
            },
            revision: { minimum: 0, title: "Revision", type: "integer" },
            version: {
              const: 1,
              default: 1,
              title: "Version",
              type: "integer",
            },
            volatile: {
              const: true,
              default: true,
              title: "Volatile",
              type: "boolean",
            },
          },
          required: ["revision", "expires_after_seconds", "events", "devices"],
          title: "VoiceSnapshot",
          type: "object",
        },
      },
      additionalProperties: false,
      properties: {
        ambient_weather: {
          anyOf: [{ $ref: "#/$defs/Forecast" }, { type: "null" }],
          default: null,
        },
        application: { $ref: "#/$defs/ApplicationSnapshot" },
        epoch: { format: "uuid", title: "Epoch", type: "string" },
        events: { $ref: "#/$defs/EventPage" },
        home: {
          items: { $ref: "#/$defs/BrowserHome" },
          title: "Home",
          type: "array",
        },
        model: {
          anyOf: [{ type: "string" }, { type: "null" }],
          title: "Model",
        },
        provider: { title: "Provider", type: "string" },
        reset: { title: "Reset", type: "boolean" },
        server_time: { title: "Server Time", type: "string" },
        session: { $ref: "#/$defs/BrowserSession" },
        version: { const: 1, default: 1, title: "Version", type: "integer" },
        voice: { $ref: "#/$defs/VoiceSnapshot" },
      },
      required: [
        "epoch",
        "reset",
        "server_time",
        "session",
        "application",
        "events",
        "voice",
        "home",
        "provider",
        "model",
      ],
      title: "BrowserFrame",
      type: "object",
    };
    var schema42 = {
      additionalProperties: false,
      properties: {
        attributes: {
          additionalProperties: true,
          title: "Attributes",
          type: "object",
        },
        capabilities: {
          items: { type: "string" },
          title: "Capabilities",
          type: "array",
        },
        entity_id: { title: "Entity Id", type: "string" },
        last_updated: {
          anyOf: [{ type: "string" }, { type: "null" }],
          title: "Last Updated",
        },
        name: { maxLength: 160, title: "Name", type: "string" },
        observed_at: {
          format: "date-time",
          title: "Observed At",
          type: "string",
        },
        power_off: { title: "Power Off", type: "boolean" },
        power_on: { title: "Power On", type: "boolean" },
        remote_commands: {
          items: { type: "string" },
          title: "Remote Commands",
          type: "array",
        },
        source: { const: "home-assistant", title: "Source", type: "string" },
        state: { maxLength: 160, title: "State", type: "string" },
      },
      required: [
        "entity_id",
        "name",
        "state",
        "source",
        "observed_at",
        "last_updated",
        "attributes",
        "capabilities",
        "remote_commands",
        "power_on",
        "power_off",
      ],
      title: "BrowserHome",
      type: "object",
    };
    var func1 = Object.prototype.hasOwnProperty;
    var func2 = require_ucs2length().default;
    var schema32 = {
      properties: {
        cache_age_seconds: {
          default: 0,
          title: "Cache Age Seconds",
          type: "number",
        },
        current: { $ref: "#/$defs/Current" },
        daily: {
          items: { $ref: "#/$defs/Day" },
          title: "Daily",
          type: "array",
        },
        fetched_at: { title: "Fetched At", type: "string" },
        freshness_ttl_seconds: {
          default: 600,
          exclusiveMinimum: 0,
          title: "Freshness Ttl Seconds",
          type: "number",
        },
        hourly: {
          items: { $ref: "#/$defs/Hour" },
          title: "Hourly",
          type: "array",
        },
        location: { $ref: "#/$defs/Location" },
        measurement_units: {
          additionalProperties: { type: "string" },
          title: "Measurement Units",
          type: "object",
        },
        source: {
          const: "open-meteo",
          default: "open-meteo",
          title: "Source",
          type: "string",
        },
        source_age_seconds: {
          anyOf: [{ minimum: 0, type: "number" }, { type: "null" }],
          default: null,
          title: "Source Age Seconds",
        },
        source_timestamp: {
          anyOf: [{ type: "string" }, { type: "null" }],
          title: "Source Timestamp",
        },
        stale: { default: false, title: "Stale", type: "boolean" },
        units: { enum: ["imperial", "metric"], title: "Units", type: "string" },
        valid_from: {
          anyOf: [{ type: "string" }, { type: "null" }],
          title: "Valid From",
        },
        valid_until: {
          anyOf: [{ type: "string" }, { type: "null" }],
          title: "Valid Until",
        },
        version: { const: 1, default: 1, title: "Version", type: "integer" },
      },
      required: [
        "location",
        "units",
        "measurement_units",
        "current",
        "hourly",
        "daily",
        "fetched_at",
        "source_timestamp",
        "valid_from",
        "valid_until",
      ],
      title: "Forecast",
      type: "object",
    };
    function validate21(
      data,
      {
        instancePath = "",
        parentData,
        parentDataProperty,
        rootData = data,
        dynamicAnchors = {},
      } = {},
    ) {
      let vErrors = null;
      let errors = 0;
      const evaluated0 = validate21.evaluated;
      if (evaluated0.dynamicProps) {
        evaluated0.props = void 0;
      }
      if (evaluated0.dynamicItems) {
        evaluated0.items = void 0;
      }
      if (errors === 0) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          let missing0;
          if (
            (data.location === void 0 && (missing0 = "location")) ||
            (data.units === void 0 && (missing0 = "units")) ||
            (data.measurement_units === void 0 &&
              (missing0 = "measurement_units")) ||
            (data.current === void 0 && (missing0 = "current")) ||
            (data.hourly === void 0 && (missing0 = "hourly")) ||
            (data.daily === void 0 && (missing0 = "daily")) ||
            (data.fetched_at === void 0 && (missing0 = "fetched_at")) ||
            (data.source_timestamp === void 0 &&
              (missing0 = "source_timestamp")) ||
            (data.valid_from === void 0 && (missing0 = "valid_from")) ||
            (data.valid_until === void 0 && (missing0 = "valid_until"))
          ) {
            validate21.errors = [
              {
                instancePath,
                schemaPath: "#/required",
                keyword: "required",
                params: { missingProperty: missing0 },
                message: "must have required property '" + missing0 + "'",
              },
            ];
            return false;
          } else {
            if (data.cache_age_seconds !== void 0) {
              const _errs1 = errors;
              if (!(typeof data.cache_age_seconds == "number")) {
                validate21.errors = [
                  {
                    instancePath: instancePath + "/cache_age_seconds",
                    schemaPath: "#/properties/cache_age_seconds/type",
                    keyword: "type",
                    params: { type: "number" },
                    message: "must be number",
                  },
                ];
                return false;
              }
              var valid0 = _errs1 === errors;
            } else {
              var valid0 = true;
            }
            if (valid0) {
              if (data.current !== void 0) {
                let data1 = data.current;
                const _errs3 = errors;
                const _errs4 = errors;
                if (errors === _errs4) {
                  if (
                    data1 &&
                    typeof data1 == "object" &&
                    !Array.isArray(data1)
                  ) {
                    let missing1;
                    if (
                      (data1.time === void 0 && (missing1 = "time")) ||
                      (data1.temperature === void 0 &&
                        (missing1 = "temperature")) ||
                      (data1.feels_like === void 0 &&
                        (missing1 = "feels_like")) ||
                      (data1.humidity_pct === void 0 &&
                        (missing1 = "humidity_pct")) ||
                      (data1.wind_speed === void 0 &&
                        (missing1 = "wind_speed")) ||
                      (data1.condition === void 0 &&
                        (missing1 = "condition")) ||
                      (data1.precipitation === void 0 &&
                        (missing1 = "precipitation"))
                    ) {
                      validate21.errors = [
                        {
                          instancePath: instancePath + "/current",
                          schemaPath: "#/$defs/Current/required",
                          keyword: "required",
                          params: { missingProperty: missing1 },
                          message:
                            "must have required property '" + missing1 + "'",
                        },
                      ];
                      return false;
                    } else {
                      if (data1.condition !== void 0) {
                        let data2 = data1.condition;
                        const _errs6 = errors;
                        const _errs7 = errors;
                        let valid3 = false;
                        const _errs8 = errors;
                        if (typeof data2 !== "string") {
                          const err0 = {
                            instancePath: instancePath + "/current/condition",
                            schemaPath:
                              "#/$defs/Current/properties/condition/anyOf/0/type",
                            keyword: "type",
                            params: { type: "string" },
                            message: "must be string",
                          };
                          if (vErrors === null) {
                            vErrors = [err0];
                          } else {
                            vErrors.push(err0);
                          }
                          errors++;
                        }
                        var _valid0 = _errs8 === errors;
                        valid3 = valid3 || _valid0;
                        const _errs10 = errors;
                        if (data2 !== null) {
                          const err1 = {
                            instancePath: instancePath + "/current/condition",
                            schemaPath:
                              "#/$defs/Current/properties/condition/anyOf/1/type",
                            keyword: "type",
                            params: { type: "null" },
                            message: "must be null",
                          };
                          if (vErrors === null) {
                            vErrors = [err1];
                          } else {
                            vErrors.push(err1);
                          }
                          errors++;
                        }
                        var _valid0 = _errs10 === errors;
                        valid3 = valid3 || _valid0;
                        if (!valid3) {
                          const err2 = {
                            instancePath: instancePath + "/current/condition",
                            schemaPath:
                              "#/$defs/Current/properties/condition/anyOf",
                            keyword: "anyOf",
                            params: {},
                            message: "must match a schema in anyOf",
                          };
                          if (vErrors === null) {
                            vErrors = [err2];
                          } else {
                            vErrors.push(err2);
                          }
                          errors++;
                          validate21.errors = vErrors;
                          return false;
                        } else {
                          errors = _errs7;
                          if (vErrors !== null) {
                            if (_errs7) {
                              vErrors.length = _errs7;
                            } else {
                              vErrors = null;
                            }
                          }
                        }
                        var valid2 = _errs6 === errors;
                      } else {
                        var valid2 = true;
                      }
                      if (valid2) {
                        if (data1.feels_like !== void 0) {
                          let data3 = data1.feels_like;
                          const _errs12 = errors;
                          const _errs13 = errors;
                          let valid4 = false;
                          const _errs14 = errors;
                          if (!(typeof data3 == "number")) {
                            const err3 = {
                              instancePath:
                                instancePath + "/current/feels_like",
                              schemaPath:
                                "#/$defs/Current/properties/feels_like/anyOf/0/type",
                              keyword: "type",
                              params: { type: "number" },
                              message: "must be number",
                            };
                            if (vErrors === null) {
                              vErrors = [err3];
                            } else {
                              vErrors.push(err3);
                            }
                            errors++;
                          }
                          var _valid1 = _errs14 === errors;
                          valid4 = valid4 || _valid1;
                          const _errs16 = errors;
                          if (data3 !== null) {
                            const err4 = {
                              instancePath:
                                instancePath + "/current/feels_like",
                              schemaPath:
                                "#/$defs/Current/properties/feels_like/anyOf/1/type",
                              keyword: "type",
                              params: { type: "null" },
                              message: "must be null",
                            };
                            if (vErrors === null) {
                              vErrors = [err4];
                            } else {
                              vErrors.push(err4);
                            }
                            errors++;
                          }
                          var _valid1 = _errs16 === errors;
                          valid4 = valid4 || _valid1;
                          if (!valid4) {
                            const err5 = {
                              instancePath:
                                instancePath + "/current/feels_like",
                              schemaPath:
                                "#/$defs/Current/properties/feels_like/anyOf",
                              keyword: "anyOf",
                              params: {},
                              message: "must match a schema in anyOf",
                            };
                            if (vErrors === null) {
                              vErrors = [err5];
                            } else {
                              vErrors.push(err5);
                            }
                            errors++;
                            validate21.errors = vErrors;
                            return false;
                          } else {
                            errors = _errs13;
                            if (vErrors !== null) {
                              if (_errs13) {
                                vErrors.length = _errs13;
                              } else {
                                vErrors = null;
                              }
                            }
                          }
                          var valid2 = _errs12 === errors;
                        } else {
                          var valid2 = true;
                        }
                        if (valid2) {
                          if (data1.humidity_pct !== void 0) {
                            let data4 = data1.humidity_pct;
                            const _errs18 = errors;
                            const _errs19 = errors;
                            let valid5 = false;
                            const _errs20 = errors;
                            if (errors === _errs20) {
                              if (typeof data4 == "number") {
                                if (data4 > 100 || isNaN(data4)) {
                                  const err6 = {
                                    instancePath:
                                      instancePath + "/current/humidity_pct",
                                    schemaPath:
                                      "#/$defs/Current/properties/humidity_pct/anyOf/0/maximum",
                                    keyword: "maximum",
                                    params: { comparison: "<=", limit: 100 },
                                    message: "must be <= 100",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err6];
                                  } else {
                                    vErrors.push(err6);
                                  }
                                  errors++;
                                } else {
                                  if (data4 < 0 || isNaN(data4)) {
                                    const err7 = {
                                      instancePath:
                                        instancePath + "/current/humidity_pct",
                                      schemaPath:
                                        "#/$defs/Current/properties/humidity_pct/anyOf/0/minimum",
                                      keyword: "minimum",
                                      params: { comparison: ">=", limit: 0 },
                                      message: "must be >= 0",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err7];
                                    } else {
                                      vErrors.push(err7);
                                    }
                                    errors++;
                                  }
                                }
                              } else {
                                const err8 = {
                                  instancePath:
                                    instancePath + "/current/humidity_pct",
                                  schemaPath:
                                    "#/$defs/Current/properties/humidity_pct/anyOf/0/type",
                                  keyword: "type",
                                  params: { type: "number" },
                                  message: "must be number",
                                };
                                if (vErrors === null) {
                                  vErrors = [err8];
                                } else {
                                  vErrors.push(err8);
                                }
                                errors++;
                              }
                            }
                            var _valid2 = _errs20 === errors;
                            valid5 = valid5 || _valid2;
                            const _errs22 = errors;
                            if (data4 !== null) {
                              const err9 = {
                                instancePath:
                                  instancePath + "/current/humidity_pct",
                                schemaPath:
                                  "#/$defs/Current/properties/humidity_pct/anyOf/1/type",
                                keyword: "type",
                                params: { type: "null" },
                                message: "must be null",
                              };
                              if (vErrors === null) {
                                vErrors = [err9];
                              } else {
                                vErrors.push(err9);
                              }
                              errors++;
                            }
                            var _valid2 = _errs22 === errors;
                            valid5 = valid5 || _valid2;
                            if (!valid5) {
                              const err10 = {
                                instancePath:
                                  instancePath + "/current/humidity_pct",
                                schemaPath:
                                  "#/$defs/Current/properties/humidity_pct/anyOf",
                                keyword: "anyOf",
                                params: {},
                                message: "must match a schema in anyOf",
                              };
                              if (vErrors === null) {
                                vErrors = [err10];
                              } else {
                                vErrors.push(err10);
                              }
                              errors++;
                              validate21.errors = vErrors;
                              return false;
                            } else {
                              errors = _errs19;
                              if (vErrors !== null) {
                                if (_errs19) {
                                  vErrors.length = _errs19;
                                } else {
                                  vErrors = null;
                                }
                              }
                            }
                            var valid2 = _errs18 === errors;
                          } else {
                            var valid2 = true;
                          }
                          if (valid2) {
                            if (data1.kind !== void 0) {
                              let data5 = data1.kind;
                              const _errs24 = errors;
                              if (typeof data5 !== "string") {
                                validate21.errors = [
                                  {
                                    instancePath:
                                      instancePath + "/current/kind",
                                    schemaPath:
                                      "#/$defs/Current/properties/kind/type",
                                    keyword: "type",
                                    params: { type: "string" },
                                    message: "must be string",
                                  },
                                ];
                                return false;
                              }
                              if ("model_estimate" !== data5) {
                                validate21.errors = [
                                  {
                                    instancePath:
                                      instancePath + "/current/kind",
                                    schemaPath:
                                      "#/$defs/Current/properties/kind/const",
                                    keyword: "const",
                                    params: { allowedValue: "model_estimate" },
                                    message: "must be equal to constant",
                                  },
                                ];
                                return false;
                              }
                              var valid2 = _errs24 === errors;
                            } else {
                              var valid2 = true;
                            }
                            if (valid2) {
                              if (data1.precipitation !== void 0) {
                                let data6 = data1.precipitation;
                                const _errs26 = errors;
                                const _errs27 = errors;
                                let valid6 = false;
                                const _errs28 = errors;
                                if (!(typeof data6 == "number")) {
                                  const err11 = {
                                    instancePath:
                                      instancePath + "/current/precipitation",
                                    schemaPath:
                                      "#/$defs/Current/properties/precipitation/anyOf/0/type",
                                    keyword: "type",
                                    params: { type: "number" },
                                    message: "must be number",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err11];
                                  } else {
                                    vErrors.push(err11);
                                  }
                                  errors++;
                                }
                                var _valid3 = _errs28 === errors;
                                valid6 = valid6 || _valid3;
                                const _errs30 = errors;
                                if (data6 !== null) {
                                  const err12 = {
                                    instancePath:
                                      instancePath + "/current/precipitation",
                                    schemaPath:
                                      "#/$defs/Current/properties/precipitation/anyOf/1/type",
                                    keyword: "type",
                                    params: { type: "null" },
                                    message: "must be null",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err12];
                                  } else {
                                    vErrors.push(err12);
                                  }
                                  errors++;
                                }
                                var _valid3 = _errs30 === errors;
                                valid6 = valid6 || _valid3;
                                if (!valid6) {
                                  const err13 = {
                                    instancePath:
                                      instancePath + "/current/precipitation",
                                    schemaPath:
                                      "#/$defs/Current/properties/precipitation/anyOf",
                                    keyword: "anyOf",
                                    params: {},
                                    message: "must match a schema in anyOf",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err13];
                                  } else {
                                    vErrors.push(err13);
                                  }
                                  errors++;
                                  validate21.errors = vErrors;
                                  return false;
                                } else {
                                  errors = _errs27;
                                  if (vErrors !== null) {
                                    if (_errs27) {
                                      vErrors.length = _errs27;
                                    } else {
                                      vErrors = null;
                                    }
                                  }
                                }
                                var valid2 = _errs26 === errors;
                              } else {
                                var valid2 = true;
                              }
                              if (valid2) {
                                if (data1.temperature !== void 0) {
                                  let data7 = data1.temperature;
                                  const _errs32 = errors;
                                  const _errs33 = errors;
                                  let valid7 = false;
                                  const _errs34 = errors;
                                  if (!(typeof data7 == "number")) {
                                    const err14 = {
                                      instancePath:
                                        instancePath + "/current/temperature",
                                      schemaPath:
                                        "#/$defs/Current/properties/temperature/anyOf/0/type",
                                      keyword: "type",
                                      params: { type: "number" },
                                      message: "must be number",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err14];
                                    } else {
                                      vErrors.push(err14);
                                    }
                                    errors++;
                                  }
                                  var _valid4 = _errs34 === errors;
                                  valid7 = valid7 || _valid4;
                                  const _errs36 = errors;
                                  if (data7 !== null) {
                                    const err15 = {
                                      instancePath:
                                        instancePath + "/current/temperature",
                                      schemaPath:
                                        "#/$defs/Current/properties/temperature/anyOf/1/type",
                                      keyword: "type",
                                      params: { type: "null" },
                                      message: "must be null",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err15];
                                    } else {
                                      vErrors.push(err15);
                                    }
                                    errors++;
                                  }
                                  var _valid4 = _errs36 === errors;
                                  valid7 = valid7 || _valid4;
                                  if (!valid7) {
                                    const err16 = {
                                      instancePath:
                                        instancePath + "/current/temperature",
                                      schemaPath:
                                        "#/$defs/Current/properties/temperature/anyOf",
                                      keyword: "anyOf",
                                      params: {},
                                      message: "must match a schema in anyOf",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err16];
                                    } else {
                                      vErrors.push(err16);
                                    }
                                    errors++;
                                    validate21.errors = vErrors;
                                    return false;
                                  } else {
                                    errors = _errs33;
                                    if (vErrors !== null) {
                                      if (_errs33) {
                                        vErrors.length = _errs33;
                                      } else {
                                        vErrors = null;
                                      }
                                    }
                                  }
                                  var valid2 = _errs32 === errors;
                                } else {
                                  var valid2 = true;
                                }
                                if (valid2) {
                                  if (data1.time !== void 0) {
                                    let data8 = data1.time;
                                    const _errs38 = errors;
                                    const _errs39 = errors;
                                    let valid8 = false;
                                    const _errs40 = errors;
                                    if (typeof data8 !== "string") {
                                      const err17 = {
                                        instancePath:
                                          instancePath + "/current/time",
                                        schemaPath:
                                          "#/$defs/Current/properties/time/anyOf/0/type",
                                        keyword: "type",
                                        params: { type: "string" },
                                        message: "must be string",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err17];
                                      } else {
                                        vErrors.push(err17);
                                      }
                                      errors++;
                                    }
                                    var _valid5 = _errs40 === errors;
                                    valid8 = valid8 || _valid5;
                                    const _errs42 = errors;
                                    if (data8 !== null) {
                                      const err18 = {
                                        instancePath:
                                          instancePath + "/current/time",
                                        schemaPath:
                                          "#/$defs/Current/properties/time/anyOf/1/type",
                                        keyword: "type",
                                        params: { type: "null" },
                                        message: "must be null",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err18];
                                      } else {
                                        vErrors.push(err18);
                                      }
                                      errors++;
                                    }
                                    var _valid5 = _errs42 === errors;
                                    valid8 = valid8 || _valid5;
                                    if (!valid8) {
                                      const err19 = {
                                        instancePath:
                                          instancePath + "/current/time",
                                        schemaPath:
                                          "#/$defs/Current/properties/time/anyOf",
                                        keyword: "anyOf",
                                        params: {},
                                        message: "must match a schema in anyOf",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err19];
                                      } else {
                                        vErrors.push(err19);
                                      }
                                      errors++;
                                      validate21.errors = vErrors;
                                      return false;
                                    } else {
                                      errors = _errs39;
                                      if (vErrors !== null) {
                                        if (_errs39) {
                                          vErrors.length = _errs39;
                                        } else {
                                          vErrors = null;
                                        }
                                      }
                                    }
                                    var valid2 = _errs38 === errors;
                                  } else {
                                    var valid2 = true;
                                  }
                                  if (valid2) {
                                    if (data1.wind_speed !== void 0) {
                                      let data9 = data1.wind_speed;
                                      const _errs44 = errors;
                                      const _errs45 = errors;
                                      let valid9 = false;
                                      const _errs46 = errors;
                                      if (!(typeof data9 == "number")) {
                                        const err20 = {
                                          instancePath:
                                            instancePath +
                                            "/current/wind_speed",
                                          schemaPath:
                                            "#/$defs/Current/properties/wind_speed/anyOf/0/type",
                                          keyword: "type",
                                          params: { type: "number" },
                                          message: "must be number",
                                        };
                                        if (vErrors === null) {
                                          vErrors = [err20];
                                        } else {
                                          vErrors.push(err20);
                                        }
                                        errors++;
                                      }
                                      var _valid6 = _errs46 === errors;
                                      valid9 = valid9 || _valid6;
                                      const _errs48 = errors;
                                      if (data9 !== null) {
                                        const err21 = {
                                          instancePath:
                                            instancePath +
                                            "/current/wind_speed",
                                          schemaPath:
                                            "#/$defs/Current/properties/wind_speed/anyOf/1/type",
                                          keyword: "type",
                                          params: { type: "null" },
                                          message: "must be null",
                                        };
                                        if (vErrors === null) {
                                          vErrors = [err21];
                                        } else {
                                          vErrors.push(err21);
                                        }
                                        errors++;
                                      }
                                      var _valid6 = _errs48 === errors;
                                      valid9 = valid9 || _valid6;
                                      if (!valid9) {
                                        const err22 = {
                                          instancePath:
                                            instancePath +
                                            "/current/wind_speed",
                                          schemaPath:
                                            "#/$defs/Current/properties/wind_speed/anyOf",
                                          keyword: "anyOf",
                                          params: {},
                                          message:
                                            "must match a schema in anyOf",
                                        };
                                        if (vErrors === null) {
                                          vErrors = [err22];
                                        } else {
                                          vErrors.push(err22);
                                        }
                                        errors++;
                                        validate21.errors = vErrors;
                                        return false;
                                      } else {
                                        errors = _errs45;
                                        if (vErrors !== null) {
                                          if (_errs45) {
                                            vErrors.length = _errs45;
                                          } else {
                                            vErrors = null;
                                          }
                                        }
                                      }
                                      var valid2 = _errs44 === errors;
                                    } else {
                                      var valid2 = true;
                                    }
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  } else {
                    validate21.errors = [
                      {
                        instancePath: instancePath + "/current",
                        schemaPath: "#/$defs/Current/type",
                        keyword: "type",
                        params: { type: "object" },
                        message: "must be object",
                      },
                    ];
                    return false;
                  }
                }
                var valid0 = _errs3 === errors;
              } else {
                var valid0 = true;
              }
              if (valid0) {
                if (data.daily !== void 0) {
                  let data10 = data.daily;
                  const _errs50 = errors;
                  if (errors === _errs50) {
                    if (Array.isArray(data10)) {
                      var valid10 = true;
                      const len0 = data10.length;
                      for (let i0 = 0; i0 < len0; i0++) {
                        let data11 = data10[i0];
                        const _errs52 = errors;
                        const _errs53 = errors;
                        if (errors === _errs53) {
                          if (
                            data11 &&
                            typeof data11 == "object" &&
                            !Array.isArray(data11)
                          ) {
                            let missing2;
                            if (
                              (data11.date === void 0 && (missing2 = "date")) ||
                              (data11.high === void 0 && (missing2 = "high")) ||
                              (data11.low === void 0 && (missing2 = "low")) ||
                              (data11.rain_probability_pct === void 0 &&
                                (missing2 = "rain_probability_pct")) ||
                              (data11.precipitation === void 0 &&
                                (missing2 = "precipitation")) ||
                              (data11.condition === void 0 &&
                                (missing2 = "condition")) ||
                              (data11.sunrise === void 0 &&
                                (missing2 = "sunrise")) ||
                              (data11.sunset === void 0 &&
                                (missing2 = "sunset"))
                            ) {
                              validate21.errors = [
                                {
                                  instancePath: instancePath + "/daily/" + i0,
                                  schemaPath: "#/$defs/Day/required",
                                  keyword: "required",
                                  params: { missingProperty: missing2 },
                                  message:
                                    "must have required property '" +
                                    missing2 +
                                    "'",
                                },
                              ];
                              return false;
                            } else {
                              if (data11.condition !== void 0) {
                                let data12 = data11.condition;
                                const _errs55 = errors;
                                const _errs56 = errors;
                                let valid13 = false;
                                const _errs57 = errors;
                                if (typeof data12 !== "string") {
                                  const err23 = {
                                    instancePath:
                                      instancePath +
                                      "/daily/" +
                                      i0 +
                                      "/condition",
                                    schemaPath:
                                      "#/$defs/Day/properties/condition/anyOf/0/type",
                                    keyword: "type",
                                    params: { type: "string" },
                                    message: "must be string",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err23];
                                  } else {
                                    vErrors.push(err23);
                                  }
                                  errors++;
                                }
                                var _valid7 = _errs57 === errors;
                                valid13 = valid13 || _valid7;
                                const _errs59 = errors;
                                if (data12 !== null) {
                                  const err24 = {
                                    instancePath:
                                      instancePath +
                                      "/daily/" +
                                      i0 +
                                      "/condition",
                                    schemaPath:
                                      "#/$defs/Day/properties/condition/anyOf/1/type",
                                    keyword: "type",
                                    params: { type: "null" },
                                    message: "must be null",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err24];
                                  } else {
                                    vErrors.push(err24);
                                  }
                                  errors++;
                                }
                                var _valid7 = _errs59 === errors;
                                valid13 = valid13 || _valid7;
                                if (!valid13) {
                                  const err25 = {
                                    instancePath:
                                      instancePath +
                                      "/daily/" +
                                      i0 +
                                      "/condition",
                                    schemaPath:
                                      "#/$defs/Day/properties/condition/anyOf",
                                    keyword: "anyOf",
                                    params: {},
                                    message: "must match a schema in anyOf",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err25];
                                  } else {
                                    vErrors.push(err25);
                                  }
                                  errors++;
                                  validate21.errors = vErrors;
                                  return false;
                                } else {
                                  errors = _errs56;
                                  if (vErrors !== null) {
                                    if (_errs56) {
                                      vErrors.length = _errs56;
                                    } else {
                                      vErrors = null;
                                    }
                                  }
                                }
                                var valid12 = _errs55 === errors;
                              } else {
                                var valid12 = true;
                              }
                              if (valid12) {
                                if (data11.date !== void 0) {
                                  const _errs61 = errors;
                                  if (typeof data11.date !== "string") {
                                    validate21.errors = [
                                      {
                                        instancePath:
                                          instancePath +
                                          "/daily/" +
                                          i0 +
                                          "/date",
                                        schemaPath:
                                          "#/$defs/Day/properties/date/type",
                                        keyword: "type",
                                        params: { type: "string" },
                                        message: "must be string",
                                      },
                                    ];
                                    return false;
                                  }
                                  var valid12 = _errs61 === errors;
                                } else {
                                  var valid12 = true;
                                }
                                if (valid12) {
                                  if (data11.high !== void 0) {
                                    let data14 = data11.high;
                                    const _errs63 = errors;
                                    const _errs64 = errors;
                                    let valid14 = false;
                                    const _errs65 = errors;
                                    if (!(typeof data14 == "number")) {
                                      const err26 = {
                                        instancePath:
                                          instancePath +
                                          "/daily/" +
                                          i0 +
                                          "/high",
                                        schemaPath:
                                          "#/$defs/Day/properties/high/anyOf/0/type",
                                        keyword: "type",
                                        params: { type: "number" },
                                        message: "must be number",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err26];
                                      } else {
                                        vErrors.push(err26);
                                      }
                                      errors++;
                                    }
                                    var _valid8 = _errs65 === errors;
                                    valid14 = valid14 || _valid8;
                                    const _errs67 = errors;
                                    if (data14 !== null) {
                                      const err27 = {
                                        instancePath:
                                          instancePath +
                                          "/daily/" +
                                          i0 +
                                          "/high",
                                        schemaPath:
                                          "#/$defs/Day/properties/high/anyOf/1/type",
                                        keyword: "type",
                                        params: { type: "null" },
                                        message: "must be null",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err27];
                                      } else {
                                        vErrors.push(err27);
                                      }
                                      errors++;
                                    }
                                    var _valid8 = _errs67 === errors;
                                    valid14 = valid14 || _valid8;
                                    if (!valid14) {
                                      const err28 = {
                                        instancePath:
                                          instancePath +
                                          "/daily/" +
                                          i0 +
                                          "/high",
                                        schemaPath:
                                          "#/$defs/Day/properties/high/anyOf",
                                        keyword: "anyOf",
                                        params: {},
                                        message: "must match a schema in anyOf",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err28];
                                      } else {
                                        vErrors.push(err28);
                                      }
                                      errors++;
                                      validate21.errors = vErrors;
                                      return false;
                                    } else {
                                      errors = _errs64;
                                      if (vErrors !== null) {
                                        if (_errs64) {
                                          vErrors.length = _errs64;
                                        } else {
                                          vErrors = null;
                                        }
                                      }
                                    }
                                    var valid12 = _errs63 === errors;
                                  } else {
                                    var valid12 = true;
                                  }
                                  if (valid12) {
                                    if (data11.kind !== void 0) {
                                      let data15 = data11.kind;
                                      const _errs69 = errors;
                                      if (typeof data15 !== "string") {
                                        validate21.errors = [
                                          {
                                            instancePath:
                                              instancePath +
                                              "/daily/" +
                                              i0 +
                                              "/kind",
                                            schemaPath:
                                              "#/$defs/Day/properties/kind/type",
                                            keyword: "type",
                                            params: { type: "string" },
                                            message: "must be string",
                                          },
                                        ];
                                        return false;
                                      }
                                      if ("forecast" !== data15) {
                                        validate21.errors = [
                                          {
                                            instancePath:
                                              instancePath +
                                              "/daily/" +
                                              i0 +
                                              "/kind",
                                            schemaPath:
                                              "#/$defs/Day/properties/kind/const",
                                            keyword: "const",
                                            params: {
                                              allowedValue: "forecast",
                                            },
                                            message:
                                              "must be equal to constant",
                                          },
                                        ];
                                        return false;
                                      }
                                      var valid12 = _errs69 === errors;
                                    } else {
                                      var valid12 = true;
                                    }
                                    if (valid12) {
                                      if (data11.low !== void 0) {
                                        let data16 = data11.low;
                                        const _errs71 = errors;
                                        const _errs72 = errors;
                                        let valid15 = false;
                                        const _errs73 = errors;
                                        if (!(typeof data16 == "number")) {
                                          const err29 = {
                                            instancePath:
                                              instancePath +
                                              "/daily/" +
                                              i0 +
                                              "/low",
                                            schemaPath:
                                              "#/$defs/Day/properties/low/anyOf/0/type",
                                            keyword: "type",
                                            params: { type: "number" },
                                            message: "must be number",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err29];
                                          } else {
                                            vErrors.push(err29);
                                          }
                                          errors++;
                                        }
                                        var _valid9 = _errs73 === errors;
                                        valid15 = valid15 || _valid9;
                                        const _errs75 = errors;
                                        if (data16 !== null) {
                                          const err30 = {
                                            instancePath:
                                              instancePath +
                                              "/daily/" +
                                              i0 +
                                              "/low",
                                            schemaPath:
                                              "#/$defs/Day/properties/low/anyOf/1/type",
                                            keyword: "type",
                                            params: { type: "null" },
                                            message: "must be null",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err30];
                                          } else {
                                            vErrors.push(err30);
                                          }
                                          errors++;
                                        }
                                        var _valid9 = _errs75 === errors;
                                        valid15 = valid15 || _valid9;
                                        if (!valid15) {
                                          const err31 = {
                                            instancePath:
                                              instancePath +
                                              "/daily/" +
                                              i0 +
                                              "/low",
                                            schemaPath:
                                              "#/$defs/Day/properties/low/anyOf",
                                            keyword: "anyOf",
                                            params: {},
                                            message:
                                              "must match a schema in anyOf",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err31];
                                          } else {
                                            vErrors.push(err31);
                                          }
                                          errors++;
                                          validate21.errors = vErrors;
                                          return false;
                                        } else {
                                          errors = _errs72;
                                          if (vErrors !== null) {
                                            if (_errs72) {
                                              vErrors.length = _errs72;
                                            } else {
                                              vErrors = null;
                                            }
                                          }
                                        }
                                        var valid12 = _errs71 === errors;
                                      } else {
                                        var valid12 = true;
                                      }
                                      if (valid12) {
                                        if (data11.precipitation !== void 0) {
                                          let data17 = data11.precipitation;
                                          const _errs77 = errors;
                                          const _errs78 = errors;
                                          let valid16 = false;
                                          const _errs79 = errors;
                                          if (!(typeof data17 == "number")) {
                                            const err32 = {
                                              instancePath:
                                                instancePath +
                                                "/daily/" +
                                                i0 +
                                                "/precipitation",
                                              schemaPath:
                                                "#/$defs/Day/properties/precipitation/anyOf/0/type",
                                              keyword: "type",
                                              params: { type: "number" },
                                              message: "must be number",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err32];
                                            } else {
                                              vErrors.push(err32);
                                            }
                                            errors++;
                                          }
                                          var _valid10 = _errs79 === errors;
                                          valid16 = valid16 || _valid10;
                                          const _errs81 = errors;
                                          if (data17 !== null) {
                                            const err33 = {
                                              instancePath:
                                                instancePath +
                                                "/daily/" +
                                                i0 +
                                                "/precipitation",
                                              schemaPath:
                                                "#/$defs/Day/properties/precipitation/anyOf/1/type",
                                              keyword: "type",
                                              params: { type: "null" },
                                              message: "must be null",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err33];
                                            } else {
                                              vErrors.push(err33);
                                            }
                                            errors++;
                                          }
                                          var _valid10 = _errs81 === errors;
                                          valid16 = valid16 || _valid10;
                                          if (!valid16) {
                                            const err34 = {
                                              instancePath:
                                                instancePath +
                                                "/daily/" +
                                                i0 +
                                                "/precipitation",
                                              schemaPath:
                                                "#/$defs/Day/properties/precipitation/anyOf",
                                              keyword: "anyOf",
                                              params: {},
                                              message:
                                                "must match a schema in anyOf",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err34];
                                            } else {
                                              vErrors.push(err34);
                                            }
                                            errors++;
                                            validate21.errors = vErrors;
                                            return false;
                                          } else {
                                            errors = _errs78;
                                            if (vErrors !== null) {
                                              if (_errs78) {
                                                vErrors.length = _errs78;
                                              } else {
                                                vErrors = null;
                                              }
                                            }
                                          }
                                          var valid12 = _errs77 === errors;
                                        } else {
                                          var valid12 = true;
                                        }
                                        if (valid12) {
                                          if (
                                            data11.rain_probability_pct !==
                                            void 0
                                          ) {
                                            let data18 =
                                              data11.rain_probability_pct;
                                            const _errs83 = errors;
                                            const _errs84 = errors;
                                            let valid17 = false;
                                            const _errs85 = errors;
                                            if (errors === _errs85) {
                                              if (typeof data18 == "number") {
                                                if (
                                                  data18 > 100 ||
                                                  isNaN(data18)
                                                ) {
                                                  const err35 = {
                                                    instancePath:
                                                      instancePath +
                                                      "/daily/" +
                                                      i0 +
                                                      "/rain_probability_pct",
                                                    schemaPath:
                                                      "#/$defs/Day/properties/rain_probability_pct/anyOf/0/maximum",
                                                    keyword: "maximum",
                                                    params: {
                                                      comparison: "<=",
                                                      limit: 100,
                                                    },
                                                    message: "must be <= 100",
                                                  };
                                                  if (vErrors === null) {
                                                    vErrors = [err35];
                                                  } else {
                                                    vErrors.push(err35);
                                                  }
                                                  errors++;
                                                } else {
                                                  if (
                                                    data18 < 0 ||
                                                    isNaN(data18)
                                                  ) {
                                                    const err36 = {
                                                      instancePath:
                                                        instancePath +
                                                        "/daily/" +
                                                        i0 +
                                                        "/rain_probability_pct",
                                                      schemaPath:
                                                        "#/$defs/Day/properties/rain_probability_pct/anyOf/0/minimum",
                                                      keyword: "minimum",
                                                      params: {
                                                        comparison: ">=",
                                                        limit: 0,
                                                      },
                                                      message: "must be >= 0",
                                                    };
                                                    if (vErrors === null) {
                                                      vErrors = [err36];
                                                    } else {
                                                      vErrors.push(err36);
                                                    }
                                                    errors++;
                                                  }
                                                }
                                              } else {
                                                const err37 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/daily/" +
                                                    i0 +
                                                    "/rain_probability_pct",
                                                  schemaPath:
                                                    "#/$defs/Day/properties/rain_probability_pct/anyOf/0/type",
                                                  keyword: "type",
                                                  params: { type: "number" },
                                                  message: "must be number",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err37];
                                                } else {
                                                  vErrors.push(err37);
                                                }
                                                errors++;
                                              }
                                            }
                                            var _valid11 = _errs85 === errors;
                                            valid17 = valid17 || _valid11;
                                            const _errs87 = errors;
                                            if (data18 !== null) {
                                              const err38 = {
                                                instancePath:
                                                  instancePath +
                                                  "/daily/" +
                                                  i0 +
                                                  "/rain_probability_pct",
                                                schemaPath:
                                                  "#/$defs/Day/properties/rain_probability_pct/anyOf/1/type",
                                                keyword: "type",
                                                params: { type: "null" },
                                                message: "must be null",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err38];
                                              } else {
                                                vErrors.push(err38);
                                              }
                                              errors++;
                                            }
                                            var _valid11 = _errs87 === errors;
                                            valid17 = valid17 || _valid11;
                                            if (!valid17) {
                                              const err39 = {
                                                instancePath:
                                                  instancePath +
                                                  "/daily/" +
                                                  i0 +
                                                  "/rain_probability_pct",
                                                schemaPath:
                                                  "#/$defs/Day/properties/rain_probability_pct/anyOf",
                                                keyword: "anyOf",
                                                params: {},
                                                message:
                                                  "must match a schema in anyOf",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err39];
                                              } else {
                                                vErrors.push(err39);
                                              }
                                              errors++;
                                              validate21.errors = vErrors;
                                              return false;
                                            } else {
                                              errors = _errs84;
                                              if (vErrors !== null) {
                                                if (_errs84) {
                                                  vErrors.length = _errs84;
                                                } else {
                                                  vErrors = null;
                                                }
                                              }
                                            }
                                            var valid12 = _errs83 === errors;
                                          } else {
                                            var valid12 = true;
                                          }
                                          if (valid12) {
                                            if (data11.sunrise !== void 0) {
                                              let data19 = data11.sunrise;
                                              const _errs89 = errors;
                                              const _errs90 = errors;
                                              let valid18 = false;
                                              const _errs91 = errors;
                                              if (typeof data19 !== "string") {
                                                const err40 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/daily/" +
                                                    i0 +
                                                    "/sunrise",
                                                  schemaPath:
                                                    "#/$defs/Day/properties/sunrise/anyOf/0/type",
                                                  keyword: "type",
                                                  params: { type: "string" },
                                                  message: "must be string",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err40];
                                                } else {
                                                  vErrors.push(err40);
                                                }
                                                errors++;
                                              }
                                              var _valid12 = _errs91 === errors;
                                              valid18 = valid18 || _valid12;
                                              const _errs93 = errors;
                                              if (data19 !== null) {
                                                const err41 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/daily/" +
                                                    i0 +
                                                    "/sunrise",
                                                  schemaPath:
                                                    "#/$defs/Day/properties/sunrise/anyOf/1/type",
                                                  keyword: "type",
                                                  params: { type: "null" },
                                                  message: "must be null",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err41];
                                                } else {
                                                  vErrors.push(err41);
                                                }
                                                errors++;
                                              }
                                              var _valid12 = _errs93 === errors;
                                              valid18 = valid18 || _valid12;
                                              if (!valid18) {
                                                const err42 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/daily/" +
                                                    i0 +
                                                    "/sunrise",
                                                  schemaPath:
                                                    "#/$defs/Day/properties/sunrise/anyOf",
                                                  keyword: "anyOf",
                                                  params: {},
                                                  message:
                                                    "must match a schema in anyOf",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err42];
                                                } else {
                                                  vErrors.push(err42);
                                                }
                                                errors++;
                                                validate21.errors = vErrors;
                                                return false;
                                              } else {
                                                errors = _errs90;
                                                if (vErrors !== null) {
                                                  if (_errs90) {
                                                    vErrors.length = _errs90;
                                                  } else {
                                                    vErrors = null;
                                                  }
                                                }
                                              }
                                              var valid12 = _errs89 === errors;
                                            } else {
                                              var valid12 = true;
                                            }
                                            if (valid12) {
                                              if (data11.sunset !== void 0) {
                                                let data20 = data11.sunset;
                                                const _errs95 = errors;
                                                const _errs96 = errors;
                                                let valid19 = false;
                                                const _errs97 = errors;
                                                if (
                                                  typeof data20 !== "string"
                                                ) {
                                                  const err43 = {
                                                    instancePath:
                                                      instancePath +
                                                      "/daily/" +
                                                      i0 +
                                                      "/sunset",
                                                    schemaPath:
                                                      "#/$defs/Day/properties/sunset/anyOf/0/type",
                                                    keyword: "type",
                                                    params: { type: "string" },
                                                    message: "must be string",
                                                  };
                                                  if (vErrors === null) {
                                                    vErrors = [err43];
                                                  } else {
                                                    vErrors.push(err43);
                                                  }
                                                  errors++;
                                                }
                                                var _valid13 =
                                                  _errs97 === errors;
                                                valid19 = valid19 || _valid13;
                                                const _errs99 = errors;
                                                if (data20 !== null) {
                                                  const err44 = {
                                                    instancePath:
                                                      instancePath +
                                                      "/daily/" +
                                                      i0 +
                                                      "/sunset",
                                                    schemaPath:
                                                      "#/$defs/Day/properties/sunset/anyOf/1/type",
                                                    keyword: "type",
                                                    params: { type: "null" },
                                                    message: "must be null",
                                                  };
                                                  if (vErrors === null) {
                                                    vErrors = [err44];
                                                  } else {
                                                    vErrors.push(err44);
                                                  }
                                                  errors++;
                                                }
                                                var _valid13 =
                                                  _errs99 === errors;
                                                valid19 = valid19 || _valid13;
                                                if (!valid19) {
                                                  const err45 = {
                                                    instancePath:
                                                      instancePath +
                                                      "/daily/" +
                                                      i0 +
                                                      "/sunset",
                                                    schemaPath:
                                                      "#/$defs/Day/properties/sunset/anyOf",
                                                    keyword: "anyOf",
                                                    params: {},
                                                    message:
                                                      "must match a schema in anyOf",
                                                  };
                                                  if (vErrors === null) {
                                                    vErrors = [err45];
                                                  } else {
                                                    vErrors.push(err45);
                                                  }
                                                  errors++;
                                                  validate21.errors = vErrors;
                                                  return false;
                                                } else {
                                                  errors = _errs96;
                                                  if (vErrors !== null) {
                                                    if (_errs96) {
                                                      vErrors.length = _errs96;
                                                    } else {
                                                      vErrors = null;
                                                    }
                                                  }
                                                }
                                                var valid12 =
                                                  _errs95 === errors;
                                              } else {
                                                var valid12 = true;
                                              }
                                            }
                                          }
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                            }
                          } else {
                            validate21.errors = [
                              {
                                instancePath: instancePath + "/daily/" + i0,
                                schemaPath: "#/$defs/Day/type",
                                keyword: "type",
                                params: { type: "object" },
                                message: "must be object",
                              },
                            ];
                            return false;
                          }
                        }
                        var valid10 = _errs52 === errors;
                        if (!valid10) {
                          break;
                        }
                      }
                    } else {
                      validate21.errors = [
                        {
                          instancePath: instancePath + "/daily",
                          schemaPath: "#/properties/daily/type",
                          keyword: "type",
                          params: { type: "array" },
                          message: "must be array",
                        },
                      ];
                      return false;
                    }
                  }
                  var valid0 = _errs50 === errors;
                } else {
                  var valid0 = true;
                }
                if (valid0) {
                  if (data.fetched_at !== void 0) {
                    const _errs101 = errors;
                    if (typeof data.fetched_at !== "string") {
                      validate21.errors = [
                        {
                          instancePath: instancePath + "/fetched_at",
                          schemaPath: "#/properties/fetched_at/type",
                          keyword: "type",
                          params: { type: "string" },
                          message: "must be string",
                        },
                      ];
                      return false;
                    }
                    var valid0 = _errs101 === errors;
                  } else {
                    var valid0 = true;
                  }
                  if (valid0) {
                    if (data.freshness_ttl_seconds !== void 0) {
                      let data22 = data.freshness_ttl_seconds;
                      const _errs103 = errors;
                      if (errors === _errs103) {
                        if (typeof data22 == "number") {
                          if (data22 <= 0 || isNaN(data22)) {
                            validate21.errors = [
                              {
                                instancePath:
                                  instancePath + "/freshness_ttl_seconds",
                                schemaPath:
                                  "#/properties/freshness_ttl_seconds/exclusiveMinimum",
                                keyword: "exclusiveMinimum",
                                params: { comparison: ">", limit: 0 },
                                message: "must be > 0",
                              },
                            ];
                            return false;
                          }
                        } else {
                          validate21.errors = [
                            {
                              instancePath:
                                instancePath + "/freshness_ttl_seconds",
                              schemaPath:
                                "#/properties/freshness_ttl_seconds/type",
                              keyword: "type",
                              params: { type: "number" },
                              message: "must be number",
                            },
                          ];
                          return false;
                        }
                      }
                      var valid0 = _errs103 === errors;
                    } else {
                      var valid0 = true;
                    }
                    if (valid0) {
                      if (data.hourly !== void 0) {
                        let data23 = data.hourly;
                        const _errs105 = errors;
                        if (errors === _errs105) {
                          if (Array.isArray(data23)) {
                            var valid20 = true;
                            const len1 = data23.length;
                            for (let i1 = 0; i1 < len1; i1++) {
                              let data24 = data23[i1];
                              const _errs107 = errors;
                              const _errs108 = errors;
                              if (errors === _errs108) {
                                if (
                                  data24 &&
                                  typeof data24 == "object" &&
                                  !Array.isArray(data24)
                                ) {
                                  let missing3;
                                  if (
                                    (data24.time === void 0 &&
                                      (missing3 = "time")) ||
                                    (data24.temperature === void 0 &&
                                      (missing3 = "temperature")) ||
                                    (data24.humidity_pct === void 0 &&
                                      (missing3 = "humidity_pct")) ||
                                    (data24.rain_probability_pct === void 0 &&
                                      (missing3 = "rain_probability_pct")) ||
                                    (data24.precipitation === void 0 &&
                                      (missing3 = "precipitation"))
                                  ) {
                                    validate21.errors = [
                                      {
                                        instancePath:
                                          instancePath + "/hourly/" + i1,
                                        schemaPath: "#/$defs/Hour/required",
                                        keyword: "required",
                                        params: { missingProperty: missing3 },
                                        message:
                                          "must have required property '" +
                                          missing3 +
                                          "'",
                                      },
                                    ];
                                    return false;
                                  } else {
                                    if (data24.humidity_pct !== void 0) {
                                      let data25 = data24.humidity_pct;
                                      const _errs110 = errors;
                                      const _errs111 = errors;
                                      let valid23 = false;
                                      const _errs112 = errors;
                                      if (errors === _errs112) {
                                        if (typeof data25 == "number") {
                                          if (data25 > 100 || isNaN(data25)) {
                                            const err46 = {
                                              instancePath:
                                                instancePath +
                                                "/hourly/" +
                                                i1 +
                                                "/humidity_pct",
                                              schemaPath:
                                                "#/$defs/Hour/properties/humidity_pct/anyOf/0/maximum",
                                              keyword: "maximum",
                                              params: {
                                                comparison: "<=",
                                                limit: 100,
                                              },
                                              message: "must be <= 100",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err46];
                                            } else {
                                              vErrors.push(err46);
                                            }
                                            errors++;
                                          } else {
                                            if (data25 < 0 || isNaN(data25)) {
                                              const err47 = {
                                                instancePath:
                                                  instancePath +
                                                  "/hourly/" +
                                                  i1 +
                                                  "/humidity_pct",
                                                schemaPath:
                                                  "#/$defs/Hour/properties/humidity_pct/anyOf/0/minimum",
                                                keyword: "minimum",
                                                params: {
                                                  comparison: ">=",
                                                  limit: 0,
                                                },
                                                message: "must be >= 0",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err47];
                                              } else {
                                                vErrors.push(err47);
                                              }
                                              errors++;
                                            }
                                          }
                                        } else {
                                          const err48 = {
                                            instancePath:
                                              instancePath +
                                              "/hourly/" +
                                              i1 +
                                              "/humidity_pct",
                                            schemaPath:
                                              "#/$defs/Hour/properties/humidity_pct/anyOf/0/type",
                                            keyword: "type",
                                            params: { type: "number" },
                                            message: "must be number",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err48];
                                          } else {
                                            vErrors.push(err48);
                                          }
                                          errors++;
                                        }
                                      }
                                      var _valid14 = _errs112 === errors;
                                      valid23 = valid23 || _valid14;
                                      const _errs114 = errors;
                                      if (data25 !== null) {
                                        const err49 = {
                                          instancePath:
                                            instancePath +
                                            "/hourly/" +
                                            i1 +
                                            "/humidity_pct",
                                          schemaPath:
                                            "#/$defs/Hour/properties/humidity_pct/anyOf/1/type",
                                          keyword: "type",
                                          params: { type: "null" },
                                          message: "must be null",
                                        };
                                        if (vErrors === null) {
                                          vErrors = [err49];
                                        } else {
                                          vErrors.push(err49);
                                        }
                                        errors++;
                                      }
                                      var _valid14 = _errs114 === errors;
                                      valid23 = valid23 || _valid14;
                                      if (!valid23) {
                                        const err50 = {
                                          instancePath:
                                            instancePath +
                                            "/hourly/" +
                                            i1 +
                                            "/humidity_pct",
                                          schemaPath:
                                            "#/$defs/Hour/properties/humidity_pct/anyOf",
                                          keyword: "anyOf",
                                          params: {},
                                          message:
                                            "must match a schema in anyOf",
                                        };
                                        if (vErrors === null) {
                                          vErrors = [err50];
                                        } else {
                                          vErrors.push(err50);
                                        }
                                        errors++;
                                        validate21.errors = vErrors;
                                        return false;
                                      } else {
                                        errors = _errs111;
                                        if (vErrors !== null) {
                                          if (_errs111) {
                                            vErrors.length = _errs111;
                                          } else {
                                            vErrors = null;
                                          }
                                        }
                                      }
                                      var valid22 = _errs110 === errors;
                                    } else {
                                      var valid22 = true;
                                    }
                                    if (valid22) {
                                      if (data24.kind !== void 0) {
                                        let data26 = data24.kind;
                                        const _errs116 = errors;
                                        if (typeof data26 !== "string") {
                                          validate21.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/hourly/" +
                                                i1 +
                                                "/kind",
                                              schemaPath:
                                                "#/$defs/Hour/properties/kind/type",
                                              keyword: "type",
                                              params: { type: "string" },
                                              message: "must be string",
                                            },
                                          ];
                                          return false;
                                        }
                                        if ("forecast" !== data26) {
                                          validate21.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/hourly/" +
                                                i1 +
                                                "/kind",
                                              schemaPath:
                                                "#/$defs/Hour/properties/kind/const",
                                              keyword: "const",
                                              params: {
                                                allowedValue: "forecast",
                                              },
                                              message:
                                                "must be equal to constant",
                                            },
                                          ];
                                          return false;
                                        }
                                        var valid22 = _errs116 === errors;
                                      } else {
                                        var valid22 = true;
                                      }
                                      if (valid22) {
                                        if (data24.precipitation !== void 0) {
                                          let data27 = data24.precipitation;
                                          const _errs118 = errors;
                                          const _errs119 = errors;
                                          let valid24 = false;
                                          const _errs120 = errors;
                                          if (!(typeof data27 == "number")) {
                                            const err51 = {
                                              instancePath:
                                                instancePath +
                                                "/hourly/" +
                                                i1 +
                                                "/precipitation",
                                              schemaPath:
                                                "#/$defs/Hour/properties/precipitation/anyOf/0/type",
                                              keyword: "type",
                                              params: { type: "number" },
                                              message: "must be number",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err51];
                                            } else {
                                              vErrors.push(err51);
                                            }
                                            errors++;
                                          }
                                          var _valid15 = _errs120 === errors;
                                          valid24 = valid24 || _valid15;
                                          const _errs122 = errors;
                                          if (data27 !== null) {
                                            const err52 = {
                                              instancePath:
                                                instancePath +
                                                "/hourly/" +
                                                i1 +
                                                "/precipitation",
                                              schemaPath:
                                                "#/$defs/Hour/properties/precipitation/anyOf/1/type",
                                              keyword: "type",
                                              params: { type: "null" },
                                              message: "must be null",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err52];
                                            } else {
                                              vErrors.push(err52);
                                            }
                                            errors++;
                                          }
                                          var _valid15 = _errs122 === errors;
                                          valid24 = valid24 || _valid15;
                                          if (!valid24) {
                                            const err53 = {
                                              instancePath:
                                                instancePath +
                                                "/hourly/" +
                                                i1 +
                                                "/precipitation",
                                              schemaPath:
                                                "#/$defs/Hour/properties/precipitation/anyOf",
                                              keyword: "anyOf",
                                              params: {},
                                              message:
                                                "must match a schema in anyOf",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err53];
                                            } else {
                                              vErrors.push(err53);
                                            }
                                            errors++;
                                            validate21.errors = vErrors;
                                            return false;
                                          } else {
                                            errors = _errs119;
                                            if (vErrors !== null) {
                                              if (_errs119) {
                                                vErrors.length = _errs119;
                                              } else {
                                                vErrors = null;
                                              }
                                            }
                                          }
                                          var valid22 = _errs118 === errors;
                                        } else {
                                          var valid22 = true;
                                        }
                                        if (valid22) {
                                          if (
                                            data24.rain_probability_pct !==
                                            void 0
                                          ) {
                                            let data28 =
                                              data24.rain_probability_pct;
                                            const _errs124 = errors;
                                            const _errs125 = errors;
                                            let valid25 = false;
                                            const _errs126 = errors;
                                            if (errors === _errs126) {
                                              if (typeof data28 == "number") {
                                                if (
                                                  data28 > 100 ||
                                                  isNaN(data28)
                                                ) {
                                                  const err54 = {
                                                    instancePath:
                                                      instancePath +
                                                      "/hourly/" +
                                                      i1 +
                                                      "/rain_probability_pct",
                                                    schemaPath:
                                                      "#/$defs/Hour/properties/rain_probability_pct/anyOf/0/maximum",
                                                    keyword: "maximum",
                                                    params: {
                                                      comparison: "<=",
                                                      limit: 100,
                                                    },
                                                    message: "must be <= 100",
                                                  };
                                                  if (vErrors === null) {
                                                    vErrors = [err54];
                                                  } else {
                                                    vErrors.push(err54);
                                                  }
                                                  errors++;
                                                } else {
                                                  if (
                                                    data28 < 0 ||
                                                    isNaN(data28)
                                                  ) {
                                                    const err55 = {
                                                      instancePath:
                                                        instancePath +
                                                        "/hourly/" +
                                                        i1 +
                                                        "/rain_probability_pct",
                                                      schemaPath:
                                                        "#/$defs/Hour/properties/rain_probability_pct/anyOf/0/minimum",
                                                      keyword: "minimum",
                                                      params: {
                                                        comparison: ">=",
                                                        limit: 0,
                                                      },
                                                      message: "must be >= 0",
                                                    };
                                                    if (vErrors === null) {
                                                      vErrors = [err55];
                                                    } else {
                                                      vErrors.push(err55);
                                                    }
                                                    errors++;
                                                  }
                                                }
                                              } else {
                                                const err56 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/hourly/" +
                                                    i1 +
                                                    "/rain_probability_pct",
                                                  schemaPath:
                                                    "#/$defs/Hour/properties/rain_probability_pct/anyOf/0/type",
                                                  keyword: "type",
                                                  params: { type: "number" },
                                                  message: "must be number",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err56];
                                                } else {
                                                  vErrors.push(err56);
                                                }
                                                errors++;
                                              }
                                            }
                                            var _valid16 = _errs126 === errors;
                                            valid25 = valid25 || _valid16;
                                            const _errs128 = errors;
                                            if (data28 !== null) {
                                              const err57 = {
                                                instancePath:
                                                  instancePath +
                                                  "/hourly/" +
                                                  i1 +
                                                  "/rain_probability_pct",
                                                schemaPath:
                                                  "#/$defs/Hour/properties/rain_probability_pct/anyOf/1/type",
                                                keyword: "type",
                                                params: { type: "null" },
                                                message: "must be null",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err57];
                                              } else {
                                                vErrors.push(err57);
                                              }
                                              errors++;
                                            }
                                            var _valid16 = _errs128 === errors;
                                            valid25 = valid25 || _valid16;
                                            if (!valid25) {
                                              const err58 = {
                                                instancePath:
                                                  instancePath +
                                                  "/hourly/" +
                                                  i1 +
                                                  "/rain_probability_pct",
                                                schemaPath:
                                                  "#/$defs/Hour/properties/rain_probability_pct/anyOf",
                                                keyword: "anyOf",
                                                params: {},
                                                message:
                                                  "must match a schema in anyOf",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err58];
                                              } else {
                                                vErrors.push(err58);
                                              }
                                              errors++;
                                              validate21.errors = vErrors;
                                              return false;
                                            } else {
                                              errors = _errs125;
                                              if (vErrors !== null) {
                                                if (_errs125) {
                                                  vErrors.length = _errs125;
                                                } else {
                                                  vErrors = null;
                                                }
                                              }
                                            }
                                            var valid22 = _errs124 === errors;
                                          } else {
                                            var valid22 = true;
                                          }
                                          if (valid22) {
                                            if (data24.temperature !== void 0) {
                                              let data29 = data24.temperature;
                                              const _errs130 = errors;
                                              const _errs131 = errors;
                                              let valid26 = false;
                                              const _errs132 = errors;
                                              if (
                                                !(typeof data29 == "number")
                                              ) {
                                                const err59 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/hourly/" +
                                                    i1 +
                                                    "/temperature",
                                                  schemaPath:
                                                    "#/$defs/Hour/properties/temperature/anyOf/0/type",
                                                  keyword: "type",
                                                  params: { type: "number" },
                                                  message: "must be number",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err59];
                                                } else {
                                                  vErrors.push(err59);
                                                }
                                                errors++;
                                              }
                                              var _valid17 =
                                                _errs132 === errors;
                                              valid26 = valid26 || _valid17;
                                              const _errs134 = errors;
                                              if (data29 !== null) {
                                                const err60 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/hourly/" +
                                                    i1 +
                                                    "/temperature",
                                                  schemaPath:
                                                    "#/$defs/Hour/properties/temperature/anyOf/1/type",
                                                  keyword: "type",
                                                  params: { type: "null" },
                                                  message: "must be null",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err60];
                                                } else {
                                                  vErrors.push(err60);
                                                }
                                                errors++;
                                              }
                                              var _valid17 =
                                                _errs134 === errors;
                                              valid26 = valid26 || _valid17;
                                              if (!valid26) {
                                                const err61 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/hourly/" +
                                                    i1 +
                                                    "/temperature",
                                                  schemaPath:
                                                    "#/$defs/Hour/properties/temperature/anyOf",
                                                  keyword: "anyOf",
                                                  params: {},
                                                  message:
                                                    "must match a schema in anyOf",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err61];
                                                } else {
                                                  vErrors.push(err61);
                                                }
                                                errors++;
                                                validate21.errors = vErrors;
                                                return false;
                                              } else {
                                                errors = _errs131;
                                                if (vErrors !== null) {
                                                  if (_errs131) {
                                                    vErrors.length = _errs131;
                                                  } else {
                                                    vErrors = null;
                                                  }
                                                }
                                              }
                                              var valid22 = _errs130 === errors;
                                            } else {
                                              var valid22 = true;
                                            }
                                            if (valid22) {
                                              if (data24.time !== void 0) {
                                                const _errs136 = errors;
                                                if (
                                                  typeof data24.time !==
                                                  "string"
                                                ) {
                                                  validate21.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/hourly/" +
                                                        i1 +
                                                        "/time",
                                                      schemaPath:
                                                        "#/$defs/Hour/properties/time/type",
                                                      keyword: "type",
                                                      params: {
                                                        type: "string",
                                                      },
                                                      message: "must be string",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                                var valid22 =
                                                  _errs136 === errors;
                                              } else {
                                                var valid22 = true;
                                              }
                                            }
                                          }
                                        }
                                      }
                                    }
                                  }
                                } else {
                                  validate21.errors = [
                                    {
                                      instancePath:
                                        instancePath + "/hourly/" + i1,
                                      schemaPath: "#/$defs/Hour/type",
                                      keyword: "type",
                                      params: { type: "object" },
                                      message: "must be object",
                                    },
                                  ];
                                  return false;
                                }
                              }
                              var valid20 = _errs107 === errors;
                              if (!valid20) {
                                break;
                              }
                            }
                          } else {
                            validate21.errors = [
                              {
                                instancePath: instancePath + "/hourly",
                                schemaPath: "#/properties/hourly/type",
                                keyword: "type",
                                params: { type: "array" },
                                message: "must be array",
                              },
                            ];
                            return false;
                          }
                        }
                        var valid0 = _errs105 === errors;
                      } else {
                        var valid0 = true;
                      }
                      if (valid0) {
                        if (data.location !== void 0) {
                          let data31 = data.location;
                          const _errs138 = errors;
                          const _errs139 = errors;
                          if (errors === _errs139) {
                            if (
                              data31 &&
                              typeof data31 == "object" &&
                              !Array.isArray(data31)
                            ) {
                              let missing4;
                              if (
                                (data31.name === void 0 &&
                                  (missing4 = "name")) ||
                                (data31.latitude === void 0 &&
                                  (missing4 = "latitude")) ||
                                (data31.longitude === void 0 &&
                                  (missing4 = "longitude")) ||
                                (data31.timezone === void 0 &&
                                  (missing4 = "timezone"))
                              ) {
                                validate21.errors = [
                                  {
                                    instancePath: instancePath + "/location",
                                    schemaPath: "#/$defs/Location/required",
                                    keyword: "required",
                                    params: { missingProperty: missing4 },
                                    message:
                                      "must have required property '" +
                                      missing4 +
                                      "'",
                                  },
                                ];
                                return false;
                              } else {
                                const _errs141 = errors;
                                for (const key0 in data31) {
                                  if (
                                    !(
                                      key0 === "latitude" ||
                                      key0 === "longitude" ||
                                      key0 === "name" ||
                                      key0 === "timezone"
                                    )
                                  ) {
                                    validate21.errors = [
                                      {
                                        instancePath:
                                          instancePath + "/location",
                                        schemaPath:
                                          "#/$defs/Location/additionalProperties",
                                        keyword: "additionalProperties",
                                        params: { additionalProperty: key0 },
                                        message:
                                          "must NOT have additional properties",
                                      },
                                    ];
                                    return false;
                                    break;
                                  }
                                }
                                if (_errs141 === errors) {
                                  if (data31.latitude !== void 0) {
                                    let data32 = data31.latitude;
                                    const _errs142 = errors;
                                    if (errors === _errs142) {
                                      if (typeof data32 == "number") {
                                        if (data32 > 90 || isNaN(data32)) {
                                          validate21.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/location/latitude",
                                              schemaPath:
                                                "#/$defs/Location/properties/latitude/maximum",
                                              keyword: "maximum",
                                              params: {
                                                comparison: "<=",
                                                limit: 90,
                                              },
                                              message: "must be <= 90",
                                            },
                                          ];
                                          return false;
                                        } else {
                                          if (data32 < -90 || isNaN(data32)) {
                                            validate21.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/location/latitude",
                                                schemaPath:
                                                  "#/$defs/Location/properties/latitude/minimum",
                                                keyword: "minimum",
                                                params: {
                                                  comparison: ">=",
                                                  limit: -90,
                                                },
                                                message: "must be >= -90",
                                              },
                                            ];
                                            return false;
                                          }
                                        }
                                      } else {
                                        validate21.errors = [
                                          {
                                            instancePath:
                                              instancePath +
                                              "/location/latitude",
                                            schemaPath:
                                              "#/$defs/Location/properties/latitude/type",
                                            keyword: "type",
                                            params: { type: "number" },
                                            message: "must be number",
                                          },
                                        ];
                                        return false;
                                      }
                                    }
                                    var valid28 = _errs142 === errors;
                                  } else {
                                    var valid28 = true;
                                  }
                                  if (valid28) {
                                    if (data31.longitude !== void 0) {
                                      let data33 = data31.longitude;
                                      const _errs144 = errors;
                                      if (errors === _errs144) {
                                        if (typeof data33 == "number") {
                                          if (data33 > 180 || isNaN(data33)) {
                                            validate21.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/location/longitude",
                                                schemaPath:
                                                  "#/$defs/Location/properties/longitude/maximum",
                                                keyword: "maximum",
                                                params: {
                                                  comparison: "<=",
                                                  limit: 180,
                                                },
                                                message: "must be <= 180",
                                              },
                                            ];
                                            return false;
                                          } else {
                                            if (
                                              data33 < -180 ||
                                              isNaN(data33)
                                            ) {
                                              validate21.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/location/longitude",
                                                  schemaPath:
                                                    "#/$defs/Location/properties/longitude/minimum",
                                                  keyword: "minimum",
                                                  params: {
                                                    comparison: ">=",
                                                    limit: -180,
                                                  },
                                                  message: "must be >= -180",
                                                },
                                              ];
                                              return false;
                                            }
                                          }
                                        } else {
                                          validate21.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/location/longitude",
                                              schemaPath:
                                                "#/$defs/Location/properties/longitude/type",
                                              keyword: "type",
                                              params: { type: "number" },
                                              message: "must be number",
                                            },
                                          ];
                                          return false;
                                        }
                                      }
                                      var valid28 = _errs144 === errors;
                                    } else {
                                      var valid28 = true;
                                    }
                                    if (valid28) {
                                      if (data31.name !== void 0) {
                                        let data34 = data31.name;
                                        const _errs146 = errors;
                                        if (errors === _errs146) {
                                          if (typeof data34 === "string") {
                                            if (func2(data34) > 240) {
                                              validate21.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/location/name",
                                                  schemaPath:
                                                    "#/$defs/Location/properties/name/maxLength",
                                                  keyword: "maxLength",
                                                  params: { limit: 240 },
                                                  message:
                                                    "must NOT have more than 240 characters",
                                                },
                                              ];
                                              return false;
                                            } else {
                                              if (func2(data34) < 1) {
                                                validate21.errors = [
                                                  {
                                                    instancePath:
                                                      instancePath +
                                                      "/location/name",
                                                    schemaPath:
                                                      "#/$defs/Location/properties/name/minLength",
                                                    keyword: "minLength",
                                                    params: { limit: 1 },
                                                    message:
                                                      "must NOT have fewer than 1 characters",
                                                  },
                                                ];
                                                return false;
                                              }
                                            }
                                          } else {
                                            validate21.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/location/name",
                                                schemaPath:
                                                  "#/$defs/Location/properties/name/type",
                                                keyword: "type",
                                                params: { type: "string" },
                                                message: "must be string",
                                              },
                                            ];
                                            return false;
                                          }
                                        }
                                        var valid28 = _errs146 === errors;
                                      } else {
                                        var valid28 = true;
                                      }
                                      if (valid28) {
                                        if (data31.timezone !== void 0) {
                                          const _errs148 = errors;
                                          if (
                                            typeof data31.timezone !== "string"
                                          ) {
                                            validate21.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/location/timezone",
                                                schemaPath:
                                                  "#/$defs/Location/properties/timezone/type",
                                                keyword: "type",
                                                params: { type: "string" },
                                                message: "must be string",
                                              },
                                            ];
                                            return false;
                                          }
                                          var valid28 = _errs148 === errors;
                                        } else {
                                          var valid28 = true;
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                            } else {
                              validate21.errors = [
                                {
                                  instancePath: instancePath + "/location",
                                  schemaPath: "#/$defs/Location/type",
                                  keyword: "type",
                                  params: { type: "object" },
                                  message: "must be object",
                                },
                              ];
                              return false;
                            }
                          }
                          var valid0 = _errs138 === errors;
                        } else {
                          var valid0 = true;
                        }
                        if (valid0) {
                          if (data.measurement_units !== void 0) {
                            let data36 = data.measurement_units;
                            const _errs150 = errors;
                            if (errors === _errs150) {
                              if (
                                data36 &&
                                typeof data36 == "object" &&
                                !Array.isArray(data36)
                              ) {
                                for (const key1 in data36) {
                                  const _errs153 = errors;
                                  if (typeof data36[key1] !== "string") {
                                    validate21.errors = [
                                      {
                                        instancePath:
                                          instancePath +
                                          "/measurement_units/" +
                                          key1
                                            .replace(/~/g, "~0")
                                            .replace(/\//g, "~1"),
                                        schemaPath:
                                          "#/properties/measurement_units/additionalProperties/type",
                                        keyword: "type",
                                        params: { type: "string" },
                                        message: "must be string",
                                      },
                                    ];
                                    return false;
                                  }
                                  var valid29 = _errs153 === errors;
                                  if (!valid29) {
                                    break;
                                  }
                                }
                              } else {
                                validate21.errors = [
                                  {
                                    instancePath:
                                      instancePath + "/measurement_units",
                                    schemaPath:
                                      "#/properties/measurement_units/type",
                                    keyword: "type",
                                    params: { type: "object" },
                                    message: "must be object",
                                  },
                                ];
                                return false;
                              }
                            }
                            var valid0 = _errs150 === errors;
                          } else {
                            var valid0 = true;
                          }
                          if (valid0) {
                            if (data.source !== void 0) {
                              let data38 = data.source;
                              const _errs155 = errors;
                              if (typeof data38 !== "string") {
                                validate21.errors = [
                                  {
                                    instancePath: instancePath + "/source",
                                    schemaPath: "#/properties/source/type",
                                    keyword: "type",
                                    params: { type: "string" },
                                    message: "must be string",
                                  },
                                ];
                                return false;
                              }
                              if ("open-meteo" !== data38) {
                                validate21.errors = [
                                  {
                                    instancePath: instancePath + "/source",
                                    schemaPath: "#/properties/source/const",
                                    keyword: "const",
                                    params: { allowedValue: "open-meteo" },
                                    message: "must be equal to constant",
                                  },
                                ];
                                return false;
                              }
                              var valid0 = _errs155 === errors;
                            } else {
                              var valid0 = true;
                            }
                            if (valid0) {
                              if (data.source_age_seconds !== void 0) {
                                let data39 = data.source_age_seconds;
                                const _errs157 = errors;
                                const _errs158 = errors;
                                let valid30 = false;
                                const _errs159 = errors;
                                if (errors === _errs159) {
                                  if (typeof data39 == "number") {
                                    if (data39 < 0 || isNaN(data39)) {
                                      const err62 = {
                                        instancePath:
                                          instancePath + "/source_age_seconds",
                                        schemaPath:
                                          "#/properties/source_age_seconds/anyOf/0/minimum",
                                        keyword: "minimum",
                                        params: { comparison: ">=", limit: 0 },
                                        message: "must be >= 0",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err62];
                                      } else {
                                        vErrors.push(err62);
                                      }
                                      errors++;
                                    }
                                  } else {
                                    const err63 = {
                                      instancePath:
                                        instancePath + "/source_age_seconds",
                                      schemaPath:
                                        "#/properties/source_age_seconds/anyOf/0/type",
                                      keyword: "type",
                                      params: { type: "number" },
                                      message: "must be number",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err63];
                                    } else {
                                      vErrors.push(err63);
                                    }
                                    errors++;
                                  }
                                }
                                var _valid18 = _errs159 === errors;
                                valid30 = valid30 || _valid18;
                                const _errs161 = errors;
                                if (data39 !== null) {
                                  const err64 = {
                                    instancePath:
                                      instancePath + "/source_age_seconds",
                                    schemaPath:
                                      "#/properties/source_age_seconds/anyOf/1/type",
                                    keyword: "type",
                                    params: { type: "null" },
                                    message: "must be null",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err64];
                                  } else {
                                    vErrors.push(err64);
                                  }
                                  errors++;
                                }
                                var _valid18 = _errs161 === errors;
                                valid30 = valid30 || _valid18;
                                if (!valid30) {
                                  const err65 = {
                                    instancePath:
                                      instancePath + "/source_age_seconds",
                                    schemaPath:
                                      "#/properties/source_age_seconds/anyOf",
                                    keyword: "anyOf",
                                    params: {},
                                    message: "must match a schema in anyOf",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err65];
                                  } else {
                                    vErrors.push(err65);
                                  }
                                  errors++;
                                  validate21.errors = vErrors;
                                  return false;
                                } else {
                                  errors = _errs158;
                                  if (vErrors !== null) {
                                    if (_errs158) {
                                      vErrors.length = _errs158;
                                    } else {
                                      vErrors = null;
                                    }
                                  }
                                }
                                var valid0 = _errs157 === errors;
                              } else {
                                var valid0 = true;
                              }
                              if (valid0) {
                                if (data.source_timestamp !== void 0) {
                                  let data40 = data.source_timestamp;
                                  const _errs163 = errors;
                                  const _errs164 = errors;
                                  let valid31 = false;
                                  const _errs165 = errors;
                                  if (typeof data40 !== "string") {
                                    const err66 = {
                                      instancePath:
                                        instancePath + "/source_timestamp",
                                      schemaPath:
                                        "#/properties/source_timestamp/anyOf/0/type",
                                      keyword: "type",
                                      params: { type: "string" },
                                      message: "must be string",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err66];
                                    } else {
                                      vErrors.push(err66);
                                    }
                                    errors++;
                                  }
                                  var _valid19 = _errs165 === errors;
                                  valid31 = valid31 || _valid19;
                                  const _errs167 = errors;
                                  if (data40 !== null) {
                                    const err67 = {
                                      instancePath:
                                        instancePath + "/source_timestamp",
                                      schemaPath:
                                        "#/properties/source_timestamp/anyOf/1/type",
                                      keyword: "type",
                                      params: { type: "null" },
                                      message: "must be null",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err67];
                                    } else {
                                      vErrors.push(err67);
                                    }
                                    errors++;
                                  }
                                  var _valid19 = _errs167 === errors;
                                  valid31 = valid31 || _valid19;
                                  if (!valid31) {
                                    const err68 = {
                                      instancePath:
                                        instancePath + "/source_timestamp",
                                      schemaPath:
                                        "#/properties/source_timestamp/anyOf",
                                      keyword: "anyOf",
                                      params: {},
                                      message: "must match a schema in anyOf",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err68];
                                    } else {
                                      vErrors.push(err68);
                                    }
                                    errors++;
                                    validate21.errors = vErrors;
                                    return false;
                                  } else {
                                    errors = _errs164;
                                    if (vErrors !== null) {
                                      if (_errs164) {
                                        vErrors.length = _errs164;
                                      } else {
                                        vErrors = null;
                                      }
                                    }
                                  }
                                  var valid0 = _errs163 === errors;
                                } else {
                                  var valid0 = true;
                                }
                                if (valid0) {
                                  if (data.stale !== void 0) {
                                    const _errs169 = errors;
                                    if (typeof data.stale !== "boolean") {
                                      validate21.errors = [
                                        {
                                          instancePath: instancePath + "/stale",
                                          schemaPath: "#/properties/stale/type",
                                          keyword: "type",
                                          params: { type: "boolean" },
                                          message: "must be boolean",
                                        },
                                      ];
                                      return false;
                                    }
                                    var valid0 = _errs169 === errors;
                                  } else {
                                    var valid0 = true;
                                  }
                                  if (valid0) {
                                    if (data.units !== void 0) {
                                      let data42 = data.units;
                                      const _errs171 = errors;
                                      if (typeof data42 !== "string") {
                                        validate21.errors = [
                                          {
                                            instancePath:
                                              instancePath + "/units",
                                            schemaPath:
                                              "#/properties/units/type",
                                            keyword: "type",
                                            params: { type: "string" },
                                            message: "must be string",
                                          },
                                        ];
                                        return false;
                                      }
                                      if (
                                        !(
                                          data42 === "imperial" ||
                                          data42 === "metric"
                                        )
                                      ) {
                                        validate21.errors = [
                                          {
                                            instancePath:
                                              instancePath + "/units",
                                            schemaPath:
                                              "#/properties/units/enum",
                                            keyword: "enum",
                                            params: {
                                              allowedValues:
                                                schema32.properties.units.enum,
                                            },
                                            message:
                                              "must be equal to one of the allowed values",
                                          },
                                        ];
                                        return false;
                                      }
                                      var valid0 = _errs171 === errors;
                                    } else {
                                      var valid0 = true;
                                    }
                                    if (valid0) {
                                      if (data.valid_from !== void 0) {
                                        let data43 = data.valid_from;
                                        const _errs173 = errors;
                                        const _errs174 = errors;
                                        let valid32 = false;
                                        const _errs175 = errors;
                                        if (typeof data43 !== "string") {
                                          const err69 = {
                                            instancePath:
                                              instancePath + "/valid_from",
                                            schemaPath:
                                              "#/properties/valid_from/anyOf/0/type",
                                            keyword: "type",
                                            params: { type: "string" },
                                            message: "must be string",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err69];
                                          } else {
                                            vErrors.push(err69);
                                          }
                                          errors++;
                                        }
                                        var _valid20 = _errs175 === errors;
                                        valid32 = valid32 || _valid20;
                                        const _errs177 = errors;
                                        if (data43 !== null) {
                                          const err70 = {
                                            instancePath:
                                              instancePath + "/valid_from",
                                            schemaPath:
                                              "#/properties/valid_from/anyOf/1/type",
                                            keyword: "type",
                                            params: { type: "null" },
                                            message: "must be null",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err70];
                                          } else {
                                            vErrors.push(err70);
                                          }
                                          errors++;
                                        }
                                        var _valid20 = _errs177 === errors;
                                        valid32 = valid32 || _valid20;
                                        if (!valid32) {
                                          const err71 = {
                                            instancePath:
                                              instancePath + "/valid_from",
                                            schemaPath:
                                              "#/properties/valid_from/anyOf",
                                            keyword: "anyOf",
                                            params: {},
                                            message:
                                              "must match a schema in anyOf",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err71];
                                          } else {
                                            vErrors.push(err71);
                                          }
                                          errors++;
                                          validate21.errors = vErrors;
                                          return false;
                                        } else {
                                          errors = _errs174;
                                          if (vErrors !== null) {
                                            if (_errs174) {
                                              vErrors.length = _errs174;
                                            } else {
                                              vErrors = null;
                                            }
                                          }
                                        }
                                        var valid0 = _errs173 === errors;
                                      } else {
                                        var valid0 = true;
                                      }
                                      if (valid0) {
                                        if (data.valid_until !== void 0) {
                                          let data44 = data.valid_until;
                                          const _errs179 = errors;
                                          const _errs180 = errors;
                                          let valid33 = false;
                                          const _errs181 = errors;
                                          if (typeof data44 !== "string") {
                                            const err72 = {
                                              instancePath:
                                                instancePath + "/valid_until",
                                              schemaPath:
                                                "#/properties/valid_until/anyOf/0/type",
                                              keyword: "type",
                                              params: { type: "string" },
                                              message: "must be string",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err72];
                                            } else {
                                              vErrors.push(err72);
                                            }
                                            errors++;
                                          }
                                          var _valid21 = _errs181 === errors;
                                          valid33 = valid33 || _valid21;
                                          const _errs183 = errors;
                                          if (data44 !== null) {
                                            const err73 = {
                                              instancePath:
                                                instancePath + "/valid_until",
                                              schemaPath:
                                                "#/properties/valid_until/anyOf/1/type",
                                              keyword: "type",
                                              params: { type: "null" },
                                              message: "must be null",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err73];
                                            } else {
                                              vErrors.push(err73);
                                            }
                                            errors++;
                                          }
                                          var _valid21 = _errs183 === errors;
                                          valid33 = valid33 || _valid21;
                                          if (!valid33) {
                                            const err74 = {
                                              instancePath:
                                                instancePath + "/valid_until",
                                              schemaPath:
                                                "#/properties/valid_until/anyOf",
                                              keyword: "anyOf",
                                              params: {},
                                              message:
                                                "must match a schema in anyOf",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err74];
                                            } else {
                                              vErrors.push(err74);
                                            }
                                            errors++;
                                            validate21.errors = vErrors;
                                            return false;
                                          } else {
                                            errors = _errs180;
                                            if (vErrors !== null) {
                                              if (_errs180) {
                                                vErrors.length = _errs180;
                                              } else {
                                                vErrors = null;
                                              }
                                            }
                                          }
                                          var valid0 = _errs179 === errors;
                                        } else {
                                          var valid0 = true;
                                        }
                                        if (valid0) {
                                          if (data.version !== void 0) {
                                            let data45 = data.version;
                                            const _errs185 = errors;
                                            if (
                                              !(
                                                typeof data45 == "number" &&
                                                !(data45 % 1) &&
                                                !isNaN(data45)
                                              )
                                            ) {
                                              validate21.errors = [
                                                {
                                                  instancePath:
                                                    instancePath + "/version",
                                                  schemaPath:
                                                    "#/properties/version/type",
                                                  keyword: "type",
                                                  params: { type: "integer" },
                                                  message: "must be integer",
                                                },
                                              ];
                                              return false;
                                            }
                                            if (1 !== data45) {
                                              validate21.errors = [
                                                {
                                                  instancePath:
                                                    instancePath + "/version",
                                                  schemaPath:
                                                    "#/properties/version/const",
                                                  keyword: "const",
                                                  params: { allowedValue: 1 },
                                                  message:
                                                    "must be equal to constant",
                                                },
                                              ];
                                              return false;
                                            }
                                            var valid0 = _errs185 === errors;
                                          } else {
                                            var valid0 = true;
                                          }
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        } else {
          validate21.errors = [
            {
              instancePath,
              schemaPath: "#/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            },
          ];
          return false;
        }
      }
      validate21.errors = vErrors;
      return errors === 0;
    }
    validate21.evaluated = {
      props: {
        cache_age_seconds: true,
        current: true,
        daily: true,
        fetched_at: true,
        freshness_ttl_seconds: true,
        hourly: true,
        location: true,
        measurement_units: true,
        source: true,
        source_age_seconds: true,
        source_timestamp: true,
        stale: true,
        units: true,
        valid_from: true,
        valid_until: true,
        version: true,
      },
      dynamicProps: false,
      dynamicItems: false,
    };
    var schema37 = {
      additionalProperties: false,
      properties: {
        alarms: {
          items: { $ref: "#/$defs/AlarmRecord" },
          title: "Alarms",
          type: "array",
        },
        availability: {
          additionalProperties: true,
          title: "Availability",
          type: "object",
        },
        devices: {
          items: { additionalProperties: true, type: "object" },
          title: "Devices",
          type: "array",
        },
        revision: { minimum: 0, title: "Revision", type: "integer" },
        timers: {
          items: { $ref: "#/$defs/TimerRecord" },
          title: "Timers",
          type: "array",
        },
        timestamp: { format: "date-time", title: "Timestamp", type: "string" },
        tools: {
          items: { additionalProperties: true, type: "object" },
          title: "Tools",
          type: "array",
        },
        version: { const: 1, default: 1, title: "Version", type: "integer" },
        views: {
          items: { additionalProperties: true, type: "object" },
          title: "Views",
          type: "array",
        },
        weather: {
          items: { $ref: "#/$defs/Forecast" },
          title: "Weather",
          type: "array",
        },
      },
      required: ["timestamp", "revision"],
      title: "ApplicationSnapshot",
      type: "object",
    };
    var schema39 = {
      additionalProperties: false,
      properties: {
        acknowledged_at: {
          anyOf: [{ format: "date-time", type: "string" }, { type: "null" }],
          title: "Acknowledged At",
        },
        created_at: {
          format: "date-time",
          title: "Created At",
          type: "string",
        },
        deadline: {
          anyOf: [{ format: "date-time", type: "string" }, { type: "null" }],
          title: "Deadline",
        },
        device_id: {
          maxLength: 64,
          minLength: 1,
          pattern: "^[a-zA-Z0-9_-]+$",
          title: "Device Id",
          type: "string",
        },
        duration_ms: {
          exclusiveMinimum: 0,
          title: "Duration Ms",
          type: "integer",
        },
        expired_at: {
          anyOf: [{ format: "date-time", type: "string" }, { type: "null" }],
          title: "Expired At",
        },
        id: { format: "uuid", title: "Id", type: "string" },
        name: { anyOf: [{ type: "string" }, { type: "null" }], title: "Name" },
        remaining_ms: { minimum: 0, title: "Remaining Ms", type: "integer" },
        status: {
          enum: ["RUNNING", "PAUSED", "EXPIRED", "CANCELLED", "ACKNOWLEDGED"],
          title: "Status",
          type: "string",
        },
        updated_at: {
          format: "date-time",
          title: "Updated At",
          type: "string",
        },
        version: { minimum: 1, title: "Version", type: "integer" },
      },
      required: [
        "id",
        "device_id",
        "name",
        "duration_ms",
        "remaining_ms",
        "status",
        "created_at",
        "deadline",
        "expired_at",
        "acknowledged_at",
        "updated_at",
        "version",
      ],
      title: "TimerRecord",
      type: "object",
    };
    var formats0 =
      /^(?:urn:uuid:)?[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
    var formats2 = require_formats().fullFormats["date-time"];
    var pattern4 = new RegExp("^[a-zA-Z0-9_-]+$", "u");
    function validate23(
      data,
      {
        instancePath = "",
        parentData,
        parentDataProperty,
        rootData = data,
        dynamicAnchors = {},
      } = {},
    ) {
      let vErrors = null;
      let errors = 0;
      const evaluated0 = validate23.evaluated;
      if (evaluated0.dynamicProps) {
        evaluated0.props = void 0;
      }
      if (evaluated0.dynamicItems) {
        evaluated0.items = void 0;
      }
      if (errors === 0) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          let missing0;
          if (
            (data.timestamp === void 0 && (missing0 = "timestamp")) ||
            (data.revision === void 0 && (missing0 = "revision"))
          ) {
            validate23.errors = [
              {
                instancePath,
                schemaPath: "#/required",
                keyword: "required",
                params: { missingProperty: missing0 },
                message: "must have required property '" + missing0 + "'",
              },
            ];
            return false;
          } else {
            const _errs1 = errors;
            for (const key0 in data) {
              if (!func1.call(schema37.properties, key0)) {
                validate23.errors = [
                  {
                    instancePath,
                    schemaPath: "#/additionalProperties",
                    keyword: "additionalProperties",
                    params: { additionalProperty: key0 },
                    message: "must NOT have additional properties",
                  },
                ];
                return false;
                break;
              }
            }
            if (_errs1 === errors) {
              if (data.alarms !== void 0) {
                let data0 = data.alarms;
                const _errs2 = errors;
                if (errors === _errs2) {
                  if (Array.isArray(data0)) {
                    var valid1 = true;
                    const len0 = data0.length;
                    for (let i0 = 0; i0 < len0; i0++) {
                      let data1 = data0[i0];
                      const _errs4 = errors;
                      const _errs5 = errors;
                      if (errors === _errs5) {
                        if (
                          data1 &&
                          typeof data1 == "object" &&
                          !Array.isArray(data1)
                        ) {
                          let missing1;
                          if (
                            (data1.alarm_id === void 0 &&
                              (missing1 = "alarm_id")) ||
                            (data1.timer_id === void 0 &&
                              (missing1 = "timer_id")) ||
                            (data1.device_id === void 0 &&
                              (missing1 = "device_id")) ||
                            (data1.expired_at === void 0 &&
                              (missing1 = "expired_at"))
                          ) {
                            validate23.errors = [
                              {
                                instancePath: instancePath + "/alarms/" + i0,
                                schemaPath: "#/$defs/AlarmRecord/required",
                                keyword: "required",
                                params: { missingProperty: missing1 },
                                message:
                                  "must have required property '" +
                                  missing1 +
                                  "'",
                              },
                            ];
                            return false;
                          } else {
                            const _errs7 = errors;
                            for (const key1 in data1) {
                              if (
                                !(
                                  key1 === "alarm_id" ||
                                  key1 === "device_id" ||
                                  key1 === "expired_at" ||
                                  key1 === "timer_id"
                                )
                              ) {
                                validate23.errors = [
                                  {
                                    instancePath:
                                      instancePath + "/alarms/" + i0,
                                    schemaPath:
                                      "#/$defs/AlarmRecord/additionalProperties",
                                    keyword: "additionalProperties",
                                    params: { additionalProperty: key1 },
                                    message:
                                      "must NOT have additional properties",
                                  },
                                ];
                                return false;
                                break;
                              }
                            }
                            if (_errs7 === errors) {
                              if (data1.alarm_id !== void 0) {
                                let data2 = data1.alarm_id;
                                const _errs8 = errors;
                                if (errors === _errs8) {
                                  if (errors === _errs8) {
                                    if (typeof data2 === "string") {
                                      if (!formats0.test(data2)) {
                                        validate23.errors = [
                                          {
                                            instancePath:
                                              instancePath +
                                              "/alarms/" +
                                              i0 +
                                              "/alarm_id",
                                            schemaPath:
                                              "#/$defs/AlarmRecord/properties/alarm_id/format",
                                            keyword: "format",
                                            params: { format: "uuid" },
                                            message: 'must match format "uuid"',
                                          },
                                        ];
                                        return false;
                                      }
                                    } else {
                                      validate23.errors = [
                                        {
                                          instancePath:
                                            instancePath +
                                            "/alarms/" +
                                            i0 +
                                            "/alarm_id",
                                          schemaPath:
                                            "#/$defs/AlarmRecord/properties/alarm_id/type",
                                          keyword: "type",
                                          params: { type: "string" },
                                          message: "must be string",
                                        },
                                      ];
                                      return false;
                                    }
                                  }
                                }
                                var valid3 = _errs8 === errors;
                              } else {
                                var valid3 = true;
                              }
                              if (valid3) {
                                if (data1.device_id !== void 0) {
                                  let data3 = data1.device_id;
                                  const _errs10 = errors;
                                  if (errors === _errs10) {
                                    if (typeof data3 === "string") {
                                      if (func2(data3) > 64) {
                                        validate23.errors = [
                                          {
                                            instancePath:
                                              instancePath +
                                              "/alarms/" +
                                              i0 +
                                              "/device_id",
                                            schemaPath:
                                              "#/$defs/AlarmRecord/properties/device_id/maxLength",
                                            keyword: "maxLength",
                                            params: { limit: 64 },
                                            message:
                                              "must NOT have more than 64 characters",
                                          },
                                        ];
                                        return false;
                                      } else {
                                        if (func2(data3) < 1) {
                                          validate23.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/alarms/" +
                                                i0 +
                                                "/device_id",
                                              schemaPath:
                                                "#/$defs/AlarmRecord/properties/device_id/minLength",
                                              keyword: "minLength",
                                              params: { limit: 1 },
                                              message:
                                                "must NOT have fewer than 1 characters",
                                            },
                                          ];
                                          return false;
                                        } else {
                                          if (!pattern4.test(data3)) {
                                            validate23.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/alarms/" +
                                                  i0 +
                                                  "/device_id",
                                                schemaPath:
                                                  "#/$defs/AlarmRecord/properties/device_id/pattern",
                                                keyword: "pattern",
                                                params: {
                                                  pattern: "^[a-zA-Z0-9_-]+$",
                                                },
                                                message:
                                                  'must match pattern "^[a-zA-Z0-9_-]+$"',
                                              },
                                            ];
                                            return false;
                                          }
                                        }
                                      }
                                    } else {
                                      validate23.errors = [
                                        {
                                          instancePath:
                                            instancePath +
                                            "/alarms/" +
                                            i0 +
                                            "/device_id",
                                          schemaPath:
                                            "#/$defs/AlarmRecord/properties/device_id/type",
                                          keyword: "type",
                                          params: { type: "string" },
                                          message: "must be string",
                                        },
                                      ];
                                      return false;
                                    }
                                  }
                                  var valid3 = _errs10 === errors;
                                } else {
                                  var valid3 = true;
                                }
                                if (valid3) {
                                  if (data1.expired_at !== void 0) {
                                    let data4 = data1.expired_at;
                                    const _errs12 = errors;
                                    if (errors === _errs12) {
                                      if (errors === _errs12) {
                                        if (typeof data4 === "string") {
                                          if (!formats2.validate(data4)) {
                                            validate23.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/alarms/" +
                                                  i0 +
                                                  "/expired_at",
                                                schemaPath:
                                                  "#/$defs/AlarmRecord/properties/expired_at/format",
                                                keyword: "format",
                                                params: { format: "date-time" },
                                                message:
                                                  'must match format "date-time"',
                                              },
                                            ];
                                            return false;
                                          }
                                        } else {
                                          validate23.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/alarms/" +
                                                i0 +
                                                "/expired_at",
                                              schemaPath:
                                                "#/$defs/AlarmRecord/properties/expired_at/type",
                                              keyword: "type",
                                              params: { type: "string" },
                                              message: "must be string",
                                            },
                                          ];
                                          return false;
                                        }
                                      }
                                    }
                                    var valid3 = _errs12 === errors;
                                  } else {
                                    var valid3 = true;
                                  }
                                  if (valid3) {
                                    if (data1.timer_id !== void 0) {
                                      let data5 = data1.timer_id;
                                      const _errs14 = errors;
                                      if (errors === _errs14) {
                                        if (errors === _errs14) {
                                          if (typeof data5 === "string") {
                                            if (!formats0.test(data5)) {
                                              validate23.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/alarms/" +
                                                    i0 +
                                                    "/timer_id",
                                                  schemaPath:
                                                    "#/$defs/AlarmRecord/properties/timer_id/format",
                                                  keyword: "format",
                                                  params: { format: "uuid" },
                                                  message:
                                                    'must match format "uuid"',
                                                },
                                              ];
                                              return false;
                                            }
                                          } else {
                                            validate23.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/alarms/" +
                                                  i0 +
                                                  "/timer_id",
                                                schemaPath:
                                                  "#/$defs/AlarmRecord/properties/timer_id/type",
                                                keyword: "type",
                                                params: { type: "string" },
                                                message: "must be string",
                                              },
                                            ];
                                            return false;
                                          }
                                        }
                                      }
                                      var valid3 = _errs14 === errors;
                                    } else {
                                      var valid3 = true;
                                    }
                                  }
                                }
                              }
                            }
                          }
                        } else {
                          validate23.errors = [
                            {
                              instancePath: instancePath + "/alarms/" + i0,
                              schemaPath: "#/$defs/AlarmRecord/type",
                              keyword: "type",
                              params: { type: "object" },
                              message: "must be object",
                            },
                          ];
                          return false;
                        }
                      }
                      var valid1 = _errs4 === errors;
                      if (!valid1) {
                        break;
                      }
                    }
                  } else {
                    validate23.errors = [
                      {
                        instancePath: instancePath + "/alarms",
                        schemaPath: "#/properties/alarms/type",
                        keyword: "type",
                        params: { type: "array" },
                        message: "must be array",
                      },
                    ];
                    return false;
                  }
                }
                var valid0 = _errs2 === errors;
              } else {
                var valid0 = true;
              }
              if (valid0) {
                if (data.availability !== void 0) {
                  let data6 = data.availability;
                  const _errs16 = errors;
                  if (errors === _errs16) {
                    if (
                      data6 &&
                      typeof data6 == "object" &&
                      !Array.isArray(data6)
                    ) {
                    } else {
                      validate23.errors = [
                        {
                          instancePath: instancePath + "/availability",
                          schemaPath: "#/properties/availability/type",
                          keyword: "type",
                          params: { type: "object" },
                          message: "must be object",
                        },
                      ];
                      return false;
                    }
                  }
                  var valid0 = _errs16 === errors;
                } else {
                  var valid0 = true;
                }
                if (valid0) {
                  if (data.devices !== void 0) {
                    let data7 = data.devices;
                    const _errs19 = errors;
                    if (errors === _errs19) {
                      if (Array.isArray(data7)) {
                        var valid4 = true;
                        const len1 = data7.length;
                        for (let i1 = 0; i1 < len1; i1++) {
                          let data8 = data7[i1];
                          const _errs21 = errors;
                          if (errors === _errs21) {
                            if (
                              data8 &&
                              typeof data8 == "object" &&
                              !Array.isArray(data8)
                            ) {
                            } else {
                              validate23.errors = [
                                {
                                  instancePath: instancePath + "/devices/" + i1,
                                  schemaPath: "#/properties/devices/items/type",
                                  keyword: "type",
                                  params: { type: "object" },
                                  message: "must be object",
                                },
                              ];
                              return false;
                            }
                          }
                          var valid4 = _errs21 === errors;
                          if (!valid4) {
                            break;
                          }
                        }
                      } else {
                        validate23.errors = [
                          {
                            instancePath: instancePath + "/devices",
                            schemaPath: "#/properties/devices/type",
                            keyword: "type",
                            params: { type: "array" },
                            message: "must be array",
                          },
                        ];
                        return false;
                      }
                    }
                    var valid0 = _errs19 === errors;
                  } else {
                    var valid0 = true;
                  }
                  if (valid0) {
                    if (data.revision !== void 0) {
                      let data9 = data.revision;
                      const _errs24 = errors;
                      if (
                        !(
                          typeof data9 == "number" &&
                          !(data9 % 1) &&
                          !isNaN(data9)
                        )
                      ) {
                        validate23.errors = [
                          {
                            instancePath: instancePath + "/revision",
                            schemaPath: "#/properties/revision/type",
                            keyword: "type",
                            params: { type: "integer" },
                            message: "must be integer",
                          },
                        ];
                        return false;
                      }
                      if (errors === _errs24) {
                        if (typeof data9 == "number") {
                          if (data9 < 0 || isNaN(data9)) {
                            validate23.errors = [
                              {
                                instancePath: instancePath + "/revision",
                                schemaPath: "#/properties/revision/minimum",
                                keyword: "minimum",
                                params: { comparison: ">=", limit: 0 },
                                message: "must be >= 0",
                              },
                            ];
                            return false;
                          }
                        }
                      }
                      var valid0 = _errs24 === errors;
                    } else {
                      var valid0 = true;
                    }
                    if (valid0) {
                      if (data.timers !== void 0) {
                        let data10 = data.timers;
                        const _errs26 = errors;
                        if (errors === _errs26) {
                          if (Array.isArray(data10)) {
                            var valid5 = true;
                            const len2 = data10.length;
                            for (let i2 = 0; i2 < len2; i2++) {
                              let data11 = data10[i2];
                              const _errs28 = errors;
                              const _errs29 = errors;
                              if (errors === _errs29) {
                                if (
                                  data11 &&
                                  typeof data11 == "object" &&
                                  !Array.isArray(data11)
                                ) {
                                  let missing2;
                                  if (
                                    (data11.id === void 0 &&
                                      (missing2 = "id")) ||
                                    (data11.device_id === void 0 &&
                                      (missing2 = "device_id")) ||
                                    (data11.name === void 0 &&
                                      (missing2 = "name")) ||
                                    (data11.duration_ms === void 0 &&
                                      (missing2 = "duration_ms")) ||
                                    (data11.remaining_ms === void 0 &&
                                      (missing2 = "remaining_ms")) ||
                                    (data11.status === void 0 &&
                                      (missing2 = "status")) ||
                                    (data11.created_at === void 0 &&
                                      (missing2 = "created_at")) ||
                                    (data11.deadline === void 0 &&
                                      (missing2 = "deadline")) ||
                                    (data11.expired_at === void 0 &&
                                      (missing2 = "expired_at")) ||
                                    (data11.acknowledged_at === void 0 &&
                                      (missing2 = "acknowledged_at")) ||
                                    (data11.updated_at === void 0 &&
                                      (missing2 = "updated_at")) ||
                                    (data11.version === void 0 &&
                                      (missing2 = "version"))
                                  ) {
                                    validate23.errors = [
                                      {
                                        instancePath:
                                          instancePath + "/timers/" + i2,
                                        schemaPath:
                                          "#/$defs/TimerRecord/required",
                                        keyword: "required",
                                        params: { missingProperty: missing2 },
                                        message:
                                          "must have required property '" +
                                          missing2 +
                                          "'",
                                      },
                                    ];
                                    return false;
                                  } else {
                                    const _errs31 = errors;
                                    for (const key2 in data11) {
                                      if (
                                        !func1.call(schema39.properties, key2)
                                      ) {
                                        validate23.errors = [
                                          {
                                            instancePath:
                                              instancePath + "/timers/" + i2,
                                            schemaPath:
                                              "#/$defs/TimerRecord/additionalProperties",
                                            keyword: "additionalProperties",
                                            params: {
                                              additionalProperty: key2,
                                            },
                                            message:
                                              "must NOT have additional properties",
                                          },
                                        ];
                                        return false;
                                        break;
                                      }
                                    }
                                    if (_errs31 === errors) {
                                      if (data11.acknowledged_at !== void 0) {
                                        let data12 = data11.acknowledged_at;
                                        const _errs32 = errors;
                                        const _errs33 = errors;
                                        let valid8 = false;
                                        const _errs34 = errors;
                                        if (errors === _errs34) {
                                          if (errors === _errs34) {
                                            if (typeof data12 === "string") {
                                              if (!formats2.validate(data12)) {
                                                const err0 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/timers/" +
                                                    i2 +
                                                    "/acknowledged_at",
                                                  schemaPath:
                                                    "#/$defs/TimerRecord/properties/acknowledged_at/anyOf/0/format",
                                                  keyword: "format",
                                                  params: {
                                                    format: "date-time",
                                                  },
                                                  message:
                                                    'must match format "date-time"',
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err0];
                                                } else {
                                                  vErrors.push(err0);
                                                }
                                                errors++;
                                              }
                                            } else {
                                              const err1 = {
                                                instancePath:
                                                  instancePath +
                                                  "/timers/" +
                                                  i2 +
                                                  "/acknowledged_at",
                                                schemaPath:
                                                  "#/$defs/TimerRecord/properties/acknowledged_at/anyOf/0/type",
                                                keyword: "type",
                                                params: { type: "string" },
                                                message: "must be string",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err1];
                                              } else {
                                                vErrors.push(err1);
                                              }
                                              errors++;
                                            }
                                          }
                                        }
                                        var _valid0 = _errs34 === errors;
                                        valid8 = valid8 || _valid0;
                                        const _errs36 = errors;
                                        if (data12 !== null) {
                                          const err2 = {
                                            instancePath:
                                              instancePath +
                                              "/timers/" +
                                              i2 +
                                              "/acknowledged_at",
                                            schemaPath:
                                              "#/$defs/TimerRecord/properties/acknowledged_at/anyOf/1/type",
                                            keyword: "type",
                                            params: { type: "null" },
                                            message: "must be null",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err2];
                                          } else {
                                            vErrors.push(err2);
                                          }
                                          errors++;
                                        }
                                        var _valid0 = _errs36 === errors;
                                        valid8 = valid8 || _valid0;
                                        if (!valid8) {
                                          const err3 = {
                                            instancePath:
                                              instancePath +
                                              "/timers/" +
                                              i2 +
                                              "/acknowledged_at",
                                            schemaPath:
                                              "#/$defs/TimerRecord/properties/acknowledged_at/anyOf",
                                            keyword: "anyOf",
                                            params: {},
                                            message:
                                              "must match a schema in anyOf",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err3];
                                          } else {
                                            vErrors.push(err3);
                                          }
                                          errors++;
                                          validate23.errors = vErrors;
                                          return false;
                                        } else {
                                          errors = _errs33;
                                          if (vErrors !== null) {
                                            if (_errs33) {
                                              vErrors.length = _errs33;
                                            } else {
                                              vErrors = null;
                                            }
                                          }
                                        }
                                        var valid7 = _errs32 === errors;
                                      } else {
                                        var valid7 = true;
                                      }
                                      if (valid7) {
                                        if (data11.created_at !== void 0) {
                                          let data13 = data11.created_at;
                                          const _errs38 = errors;
                                          if (errors === _errs38) {
                                            if (errors === _errs38) {
                                              if (typeof data13 === "string") {
                                                if (
                                                  !formats2.validate(data13)
                                                ) {
                                                  validate23.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/timers/" +
                                                        i2 +
                                                        "/created_at",
                                                      schemaPath:
                                                        "#/$defs/TimerRecord/properties/created_at/format",
                                                      keyword: "format",
                                                      params: {
                                                        format: "date-time",
                                                      },
                                                      message:
                                                        'must match format "date-time"',
                                                    },
                                                  ];
                                                  return false;
                                                }
                                              } else {
                                                validate23.errors = [
                                                  {
                                                    instancePath:
                                                      instancePath +
                                                      "/timers/" +
                                                      i2 +
                                                      "/created_at",
                                                    schemaPath:
                                                      "#/$defs/TimerRecord/properties/created_at/type",
                                                    keyword: "type",
                                                    params: { type: "string" },
                                                    message: "must be string",
                                                  },
                                                ];
                                                return false;
                                              }
                                            }
                                          }
                                          var valid7 = _errs38 === errors;
                                        } else {
                                          var valid7 = true;
                                        }
                                        if (valid7) {
                                          if (data11.deadline !== void 0) {
                                            let data14 = data11.deadline;
                                            const _errs40 = errors;
                                            const _errs41 = errors;
                                            let valid9 = false;
                                            const _errs42 = errors;
                                            if (errors === _errs42) {
                                              if (errors === _errs42) {
                                                if (
                                                  typeof data14 === "string"
                                                ) {
                                                  if (
                                                    !formats2.validate(data14)
                                                  ) {
                                                    const err4 = {
                                                      instancePath:
                                                        instancePath +
                                                        "/timers/" +
                                                        i2 +
                                                        "/deadline",
                                                      schemaPath:
                                                        "#/$defs/TimerRecord/properties/deadline/anyOf/0/format",
                                                      keyword: "format",
                                                      params: {
                                                        format: "date-time",
                                                      },
                                                      message:
                                                        'must match format "date-time"',
                                                    };
                                                    if (vErrors === null) {
                                                      vErrors = [err4];
                                                    } else {
                                                      vErrors.push(err4);
                                                    }
                                                    errors++;
                                                  }
                                                } else {
                                                  const err5 = {
                                                    instancePath:
                                                      instancePath +
                                                      "/timers/" +
                                                      i2 +
                                                      "/deadline",
                                                    schemaPath:
                                                      "#/$defs/TimerRecord/properties/deadline/anyOf/0/type",
                                                    keyword: "type",
                                                    params: { type: "string" },
                                                    message: "must be string",
                                                  };
                                                  if (vErrors === null) {
                                                    vErrors = [err5];
                                                  } else {
                                                    vErrors.push(err5);
                                                  }
                                                  errors++;
                                                }
                                              }
                                            }
                                            var _valid1 = _errs42 === errors;
                                            valid9 = valid9 || _valid1;
                                            const _errs44 = errors;
                                            if (data14 !== null) {
                                              const err6 = {
                                                instancePath:
                                                  instancePath +
                                                  "/timers/" +
                                                  i2 +
                                                  "/deadline",
                                                schemaPath:
                                                  "#/$defs/TimerRecord/properties/deadline/anyOf/1/type",
                                                keyword: "type",
                                                params: { type: "null" },
                                                message: "must be null",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err6];
                                              } else {
                                                vErrors.push(err6);
                                              }
                                              errors++;
                                            }
                                            var _valid1 = _errs44 === errors;
                                            valid9 = valid9 || _valid1;
                                            if (!valid9) {
                                              const err7 = {
                                                instancePath:
                                                  instancePath +
                                                  "/timers/" +
                                                  i2 +
                                                  "/deadline",
                                                schemaPath:
                                                  "#/$defs/TimerRecord/properties/deadline/anyOf",
                                                keyword: "anyOf",
                                                params: {},
                                                message:
                                                  "must match a schema in anyOf",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err7];
                                              } else {
                                                vErrors.push(err7);
                                              }
                                              errors++;
                                              validate23.errors = vErrors;
                                              return false;
                                            } else {
                                              errors = _errs41;
                                              if (vErrors !== null) {
                                                if (_errs41) {
                                                  vErrors.length = _errs41;
                                                } else {
                                                  vErrors = null;
                                                }
                                              }
                                            }
                                            var valid7 = _errs40 === errors;
                                          } else {
                                            var valid7 = true;
                                          }
                                          if (valid7) {
                                            if (data11.device_id !== void 0) {
                                              let data15 = data11.device_id;
                                              const _errs46 = errors;
                                              if (errors === _errs46) {
                                                if (
                                                  typeof data15 === "string"
                                                ) {
                                                  if (func2(data15) > 64) {
                                                    validate23.errors = [
                                                      {
                                                        instancePath:
                                                          instancePath +
                                                          "/timers/" +
                                                          i2 +
                                                          "/device_id",
                                                        schemaPath:
                                                          "#/$defs/TimerRecord/properties/device_id/maxLength",
                                                        keyword: "maxLength",
                                                        params: { limit: 64 },
                                                        message:
                                                          "must NOT have more than 64 characters",
                                                      },
                                                    ];
                                                    return false;
                                                  } else {
                                                    if (func2(data15) < 1) {
                                                      validate23.errors = [
                                                        {
                                                          instancePath:
                                                            instancePath +
                                                            "/timers/" +
                                                            i2 +
                                                            "/device_id",
                                                          schemaPath:
                                                            "#/$defs/TimerRecord/properties/device_id/minLength",
                                                          keyword: "minLength",
                                                          params: { limit: 1 },
                                                          message:
                                                            "must NOT have fewer than 1 characters",
                                                        },
                                                      ];
                                                      return false;
                                                    } else {
                                                      if (
                                                        !pattern4.test(data15)
                                                      ) {
                                                        validate23.errors = [
                                                          {
                                                            instancePath:
                                                              instancePath +
                                                              "/timers/" +
                                                              i2 +
                                                              "/device_id",
                                                            schemaPath:
                                                              "#/$defs/TimerRecord/properties/device_id/pattern",
                                                            keyword: "pattern",
                                                            params: {
                                                              pattern:
                                                                "^[a-zA-Z0-9_-]+$",
                                                            },
                                                            message:
                                                              'must match pattern "^[a-zA-Z0-9_-]+$"',
                                                          },
                                                        ];
                                                        return false;
                                                      }
                                                    }
                                                  }
                                                } else {
                                                  validate23.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/timers/" +
                                                        i2 +
                                                        "/device_id",
                                                      schemaPath:
                                                        "#/$defs/TimerRecord/properties/device_id/type",
                                                      keyword: "type",
                                                      params: {
                                                        type: "string",
                                                      },
                                                      message: "must be string",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                              }
                                              var valid7 = _errs46 === errors;
                                            } else {
                                              var valid7 = true;
                                            }
                                            if (valid7) {
                                              if (
                                                data11.duration_ms !== void 0
                                              ) {
                                                let data16 = data11.duration_ms;
                                                const _errs48 = errors;
                                                if (
                                                  !(
                                                    typeof data16 == "number" &&
                                                    !(data16 % 1) &&
                                                    !isNaN(data16)
                                                  )
                                                ) {
                                                  validate23.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/timers/" +
                                                        i2 +
                                                        "/duration_ms",
                                                      schemaPath:
                                                        "#/$defs/TimerRecord/properties/duration_ms/type",
                                                      keyword: "type",
                                                      params: {
                                                        type: "integer",
                                                      },
                                                      message:
                                                        "must be integer",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                                if (errors === _errs48) {
                                                  if (
                                                    typeof data16 == "number"
                                                  ) {
                                                    if (
                                                      data16 <= 0 ||
                                                      isNaN(data16)
                                                    ) {
                                                      validate23.errors = [
                                                        {
                                                          instancePath:
                                                            instancePath +
                                                            "/timers/" +
                                                            i2 +
                                                            "/duration_ms",
                                                          schemaPath:
                                                            "#/$defs/TimerRecord/properties/duration_ms/exclusiveMinimum",
                                                          keyword:
                                                            "exclusiveMinimum",
                                                          params: {
                                                            comparison: ">",
                                                            limit: 0,
                                                          },
                                                          message:
                                                            "must be > 0",
                                                        },
                                                      ];
                                                      return false;
                                                    }
                                                  }
                                                }
                                                var valid7 = _errs48 === errors;
                                              } else {
                                                var valid7 = true;
                                              }
                                              if (valid7) {
                                                if (
                                                  data11.expired_at !== void 0
                                                ) {
                                                  let data17 =
                                                    data11.expired_at;
                                                  const _errs50 = errors;
                                                  const _errs51 = errors;
                                                  let valid10 = false;
                                                  const _errs52 = errors;
                                                  if (errors === _errs52) {
                                                    if (errors === _errs52) {
                                                      if (
                                                        typeof data17 ===
                                                        "string"
                                                      ) {
                                                        if (
                                                          !formats2.validate(
                                                            data17,
                                                          )
                                                        ) {
                                                          const err8 = {
                                                            instancePath:
                                                              instancePath +
                                                              "/timers/" +
                                                              i2 +
                                                              "/expired_at",
                                                            schemaPath:
                                                              "#/$defs/TimerRecord/properties/expired_at/anyOf/0/format",
                                                            keyword: "format",
                                                            params: {
                                                              format:
                                                                "date-time",
                                                            },
                                                            message:
                                                              'must match format "date-time"',
                                                          };
                                                          if (
                                                            vErrors === null
                                                          ) {
                                                            vErrors = [err8];
                                                          } else {
                                                            vErrors.push(err8);
                                                          }
                                                          errors++;
                                                        }
                                                      } else {
                                                        const err9 = {
                                                          instancePath:
                                                            instancePath +
                                                            "/timers/" +
                                                            i2 +
                                                            "/expired_at",
                                                          schemaPath:
                                                            "#/$defs/TimerRecord/properties/expired_at/anyOf/0/type",
                                                          keyword: "type",
                                                          params: {
                                                            type: "string",
                                                          },
                                                          message:
                                                            "must be string",
                                                        };
                                                        if (vErrors === null) {
                                                          vErrors = [err9];
                                                        } else {
                                                          vErrors.push(err9);
                                                        }
                                                        errors++;
                                                      }
                                                    }
                                                  }
                                                  var _valid2 =
                                                    _errs52 === errors;
                                                  valid10 = valid10 || _valid2;
                                                  const _errs54 = errors;
                                                  if (data17 !== null) {
                                                    const err10 = {
                                                      instancePath:
                                                        instancePath +
                                                        "/timers/" +
                                                        i2 +
                                                        "/expired_at",
                                                      schemaPath:
                                                        "#/$defs/TimerRecord/properties/expired_at/anyOf/1/type",
                                                      keyword: "type",
                                                      params: { type: "null" },
                                                      message: "must be null",
                                                    };
                                                    if (vErrors === null) {
                                                      vErrors = [err10];
                                                    } else {
                                                      vErrors.push(err10);
                                                    }
                                                    errors++;
                                                  }
                                                  var _valid2 =
                                                    _errs54 === errors;
                                                  valid10 = valid10 || _valid2;
                                                  if (!valid10) {
                                                    const err11 = {
                                                      instancePath:
                                                        instancePath +
                                                        "/timers/" +
                                                        i2 +
                                                        "/expired_at",
                                                      schemaPath:
                                                        "#/$defs/TimerRecord/properties/expired_at/anyOf",
                                                      keyword: "anyOf",
                                                      params: {},
                                                      message:
                                                        "must match a schema in anyOf",
                                                    };
                                                    if (vErrors === null) {
                                                      vErrors = [err11];
                                                    } else {
                                                      vErrors.push(err11);
                                                    }
                                                    errors++;
                                                    validate23.errors = vErrors;
                                                    return false;
                                                  } else {
                                                    errors = _errs51;
                                                    if (vErrors !== null) {
                                                      if (_errs51) {
                                                        vErrors.length =
                                                          _errs51;
                                                      } else {
                                                        vErrors = null;
                                                      }
                                                    }
                                                  }
                                                  var valid7 =
                                                    _errs50 === errors;
                                                } else {
                                                  var valid7 = true;
                                                }
                                                if (valid7) {
                                                  if (data11.id !== void 0) {
                                                    let data18 = data11.id;
                                                    const _errs56 = errors;
                                                    if (errors === _errs56) {
                                                      if (errors === _errs56) {
                                                        if (
                                                          typeof data18 ===
                                                          "string"
                                                        ) {
                                                          if (
                                                            !formats0.test(
                                                              data18,
                                                            )
                                                          ) {
                                                            validate23.errors =
                                                              [
                                                                {
                                                                  instancePath:
                                                                    instancePath +
                                                                    "/timers/" +
                                                                    i2 +
                                                                    "/id",
                                                                  schemaPath:
                                                                    "#/$defs/TimerRecord/properties/id/format",
                                                                  keyword:
                                                                    "format",
                                                                  params: {
                                                                    format:
                                                                      "uuid",
                                                                  },
                                                                  message:
                                                                    'must match format "uuid"',
                                                                },
                                                              ];
                                                            return false;
                                                          }
                                                        } else {
                                                          validate23.errors = [
                                                            {
                                                              instancePath:
                                                                instancePath +
                                                                "/timers/" +
                                                                i2 +
                                                                "/id",
                                                              schemaPath:
                                                                "#/$defs/TimerRecord/properties/id/type",
                                                              keyword: "type",
                                                              params: {
                                                                type: "string",
                                                              },
                                                              message:
                                                                "must be string",
                                                            },
                                                          ];
                                                          return false;
                                                        }
                                                      }
                                                    }
                                                    var valid7 =
                                                      _errs56 === errors;
                                                  } else {
                                                    var valid7 = true;
                                                  }
                                                  if (valid7) {
                                                    if (
                                                      data11.name !== void 0
                                                    ) {
                                                      let data19 = data11.name;
                                                      const _errs58 = errors;
                                                      const _errs59 = errors;
                                                      let valid11 = false;
                                                      const _errs60 = errors;
                                                      if (
                                                        typeof data19 !==
                                                        "string"
                                                      ) {
                                                        const err12 = {
                                                          instancePath:
                                                            instancePath +
                                                            "/timers/" +
                                                            i2 +
                                                            "/name",
                                                          schemaPath:
                                                            "#/$defs/TimerRecord/properties/name/anyOf/0/type",
                                                          keyword: "type",
                                                          params: {
                                                            type: "string",
                                                          },
                                                          message:
                                                            "must be string",
                                                        };
                                                        if (vErrors === null) {
                                                          vErrors = [err12];
                                                        } else {
                                                          vErrors.push(err12);
                                                        }
                                                        errors++;
                                                      }
                                                      var _valid3 =
                                                        _errs60 === errors;
                                                      valid11 =
                                                        valid11 || _valid3;
                                                      const _errs62 = errors;
                                                      if (data19 !== null) {
                                                        const err13 = {
                                                          instancePath:
                                                            instancePath +
                                                            "/timers/" +
                                                            i2 +
                                                            "/name",
                                                          schemaPath:
                                                            "#/$defs/TimerRecord/properties/name/anyOf/1/type",
                                                          keyword: "type",
                                                          params: {
                                                            type: "null",
                                                          },
                                                          message:
                                                            "must be null",
                                                        };
                                                        if (vErrors === null) {
                                                          vErrors = [err13];
                                                        } else {
                                                          vErrors.push(err13);
                                                        }
                                                        errors++;
                                                      }
                                                      var _valid3 =
                                                        _errs62 === errors;
                                                      valid11 =
                                                        valid11 || _valid3;
                                                      if (!valid11) {
                                                        const err14 = {
                                                          instancePath:
                                                            instancePath +
                                                            "/timers/" +
                                                            i2 +
                                                            "/name",
                                                          schemaPath:
                                                            "#/$defs/TimerRecord/properties/name/anyOf",
                                                          keyword: "anyOf",
                                                          params: {},
                                                          message:
                                                            "must match a schema in anyOf",
                                                        };
                                                        if (vErrors === null) {
                                                          vErrors = [err14];
                                                        } else {
                                                          vErrors.push(err14);
                                                        }
                                                        errors++;
                                                        validate23.errors =
                                                          vErrors;
                                                        return false;
                                                      } else {
                                                        errors = _errs59;
                                                        if (vErrors !== null) {
                                                          if (_errs59) {
                                                            vErrors.length =
                                                              _errs59;
                                                          } else {
                                                            vErrors = null;
                                                          }
                                                        }
                                                      }
                                                      var valid7 =
                                                        _errs58 === errors;
                                                    } else {
                                                      var valid7 = true;
                                                    }
                                                    if (valid7) {
                                                      if (
                                                        data11.remaining_ms !==
                                                        void 0
                                                      ) {
                                                        let data20 =
                                                          data11.remaining_ms;
                                                        const _errs64 = errors;
                                                        if (
                                                          !(
                                                            typeof data20 ==
                                                              "number" &&
                                                            !(data20 % 1) &&
                                                            !isNaN(data20)
                                                          )
                                                        ) {
                                                          validate23.errors = [
                                                            {
                                                              instancePath:
                                                                instancePath +
                                                                "/timers/" +
                                                                i2 +
                                                                "/remaining_ms",
                                                              schemaPath:
                                                                "#/$defs/TimerRecord/properties/remaining_ms/type",
                                                              keyword: "type",
                                                              params: {
                                                                type: "integer",
                                                              },
                                                              message:
                                                                "must be integer",
                                                            },
                                                          ];
                                                          return false;
                                                        }
                                                        if (
                                                          errors === _errs64
                                                        ) {
                                                          if (
                                                            typeof data20 ==
                                                            "number"
                                                          ) {
                                                            if (
                                                              data20 < 0 ||
                                                              isNaN(data20)
                                                            ) {
                                                              validate23.errors =
                                                                [
                                                                  {
                                                                    instancePath:
                                                                      instancePath +
                                                                      "/timers/" +
                                                                      i2 +
                                                                      "/remaining_ms",
                                                                    schemaPath:
                                                                      "#/$defs/TimerRecord/properties/remaining_ms/minimum",
                                                                    keyword:
                                                                      "minimum",
                                                                    params: {
                                                                      comparison:
                                                                        ">=",
                                                                      limit: 0,
                                                                    },
                                                                    message:
                                                                      "must be >= 0",
                                                                  },
                                                                ];
                                                              return false;
                                                            }
                                                          }
                                                        }
                                                        var valid7 =
                                                          _errs64 === errors;
                                                      } else {
                                                        var valid7 = true;
                                                      }
                                                      if (valid7) {
                                                        if (
                                                          data11.status !==
                                                          void 0
                                                        ) {
                                                          let data21 =
                                                            data11.status;
                                                          const _errs66 =
                                                            errors;
                                                          if (
                                                            typeof data21 !==
                                                            "string"
                                                          ) {
                                                            validate23.errors =
                                                              [
                                                                {
                                                                  instancePath:
                                                                    instancePath +
                                                                    "/timers/" +
                                                                    i2 +
                                                                    "/status",
                                                                  schemaPath:
                                                                    "#/$defs/TimerRecord/properties/status/type",
                                                                  keyword:
                                                                    "type",
                                                                  params: {
                                                                    type: "string",
                                                                  },
                                                                  message:
                                                                    "must be string",
                                                                },
                                                              ];
                                                            return false;
                                                          }
                                                          if (
                                                            !(
                                                              data21 ===
                                                                "RUNNING" ||
                                                              data21 ===
                                                                "PAUSED" ||
                                                              data21 ===
                                                                "EXPIRED" ||
                                                              data21 ===
                                                                "CANCELLED" ||
                                                              data21 ===
                                                                "ACKNOWLEDGED"
                                                            )
                                                          ) {
                                                            validate23.errors =
                                                              [
                                                                {
                                                                  instancePath:
                                                                    instancePath +
                                                                    "/timers/" +
                                                                    i2 +
                                                                    "/status",
                                                                  schemaPath:
                                                                    "#/$defs/TimerRecord/properties/status/enum",
                                                                  keyword:
                                                                    "enum",
                                                                  params: {
                                                                    allowedValues:
                                                                      schema39
                                                                        .properties
                                                                        .status
                                                                        .enum,
                                                                  },
                                                                  message:
                                                                    "must be equal to one of the allowed values",
                                                                },
                                                              ];
                                                            return false;
                                                          }
                                                          var valid7 =
                                                            _errs66 === errors;
                                                        } else {
                                                          var valid7 = true;
                                                        }
                                                        if (valid7) {
                                                          if (
                                                            data11.updated_at !==
                                                            void 0
                                                          ) {
                                                            let data22 =
                                                              data11.updated_at;
                                                            const _errs68 =
                                                              errors;
                                                            if (
                                                              errors === _errs68
                                                            ) {
                                                              if (
                                                                errors ===
                                                                _errs68
                                                              ) {
                                                                if (
                                                                  typeof data22 ===
                                                                  "string"
                                                                ) {
                                                                  if (
                                                                    !formats2.validate(
                                                                      data22,
                                                                    )
                                                                  ) {
                                                                    validate23.errors =
                                                                      [
                                                                        {
                                                                          instancePath:
                                                                            instancePath +
                                                                            "/timers/" +
                                                                            i2 +
                                                                            "/updated_at",
                                                                          schemaPath:
                                                                            "#/$defs/TimerRecord/properties/updated_at/format",
                                                                          keyword:
                                                                            "format",
                                                                          params:
                                                                            {
                                                                              format:
                                                                                "date-time",
                                                                            },
                                                                          message:
                                                                            'must match format "date-time"',
                                                                        },
                                                                      ];
                                                                    return false;
                                                                  }
                                                                } else {
                                                                  validate23.errors =
                                                                    [
                                                                      {
                                                                        instancePath:
                                                                          instancePath +
                                                                          "/timers/" +
                                                                          i2 +
                                                                          "/updated_at",
                                                                        schemaPath:
                                                                          "#/$defs/TimerRecord/properties/updated_at/type",
                                                                        keyword:
                                                                          "type",
                                                                        params:
                                                                          {
                                                                            type: "string",
                                                                          },
                                                                        message:
                                                                          "must be string",
                                                                      },
                                                                    ];
                                                                  return false;
                                                                }
                                                              }
                                                            }
                                                            var valid7 =
                                                              _errs68 ===
                                                              errors;
                                                          } else {
                                                            var valid7 = true;
                                                          }
                                                          if (valid7) {
                                                            if (
                                                              data11.version !==
                                                              void 0
                                                            ) {
                                                              let data23 =
                                                                data11.version;
                                                              const _errs70 =
                                                                errors;
                                                              if (
                                                                !(
                                                                  typeof data23 ==
                                                                    "number" &&
                                                                  !(
                                                                    data23 % 1
                                                                  ) &&
                                                                  !isNaN(data23)
                                                                )
                                                              ) {
                                                                validate23.errors =
                                                                  [
                                                                    {
                                                                      instancePath:
                                                                        instancePath +
                                                                        "/timers/" +
                                                                        i2 +
                                                                        "/version",
                                                                      schemaPath:
                                                                        "#/$defs/TimerRecord/properties/version/type",
                                                                      keyword:
                                                                        "type",
                                                                      params: {
                                                                        type: "integer",
                                                                      },
                                                                      message:
                                                                        "must be integer",
                                                                    },
                                                                  ];
                                                                return false;
                                                              }
                                                              if (
                                                                errors ===
                                                                _errs70
                                                              ) {
                                                                if (
                                                                  typeof data23 ==
                                                                  "number"
                                                                ) {
                                                                  if (
                                                                    data23 <
                                                                      1 ||
                                                                    isNaN(
                                                                      data23,
                                                                    )
                                                                  ) {
                                                                    validate23.errors =
                                                                      [
                                                                        {
                                                                          instancePath:
                                                                            instancePath +
                                                                            "/timers/" +
                                                                            i2 +
                                                                            "/version",
                                                                          schemaPath:
                                                                            "#/$defs/TimerRecord/properties/version/minimum",
                                                                          keyword:
                                                                            "minimum",
                                                                          params:
                                                                            {
                                                                              comparison:
                                                                                ">=",
                                                                              limit: 1,
                                                                            },
                                                                          message:
                                                                            "must be >= 1",
                                                                        },
                                                                      ];
                                                                    return false;
                                                                  }
                                                                }
                                                              }
                                                              var valid7 =
                                                                _errs70 ===
                                                                errors;
                                                            } else {
                                                              var valid7 = true;
                                                            }
                                                          }
                                                        }
                                                      }
                                                    }
                                                  }
                                                }
                                              }
                                            }
                                          }
                                        }
                                      }
                                    }
                                  }
                                } else {
                                  validate23.errors = [
                                    {
                                      instancePath:
                                        instancePath + "/timers/" + i2,
                                      schemaPath: "#/$defs/TimerRecord/type",
                                      keyword: "type",
                                      params: { type: "object" },
                                      message: "must be object",
                                    },
                                  ];
                                  return false;
                                }
                              }
                              var valid5 = _errs28 === errors;
                              if (!valid5) {
                                break;
                              }
                            }
                          } else {
                            validate23.errors = [
                              {
                                instancePath: instancePath + "/timers",
                                schemaPath: "#/properties/timers/type",
                                keyword: "type",
                                params: { type: "array" },
                                message: "must be array",
                              },
                            ];
                            return false;
                          }
                        }
                        var valid0 = _errs26 === errors;
                      } else {
                        var valid0 = true;
                      }
                      if (valid0) {
                        if (data.timestamp !== void 0) {
                          let data24 = data.timestamp;
                          const _errs72 = errors;
                          if (errors === _errs72) {
                            if (errors === _errs72) {
                              if (typeof data24 === "string") {
                                if (!formats2.validate(data24)) {
                                  validate23.errors = [
                                    {
                                      instancePath: instancePath + "/timestamp",
                                      schemaPath:
                                        "#/properties/timestamp/format",
                                      keyword: "format",
                                      params: { format: "date-time" },
                                      message: 'must match format "date-time"',
                                    },
                                  ];
                                  return false;
                                }
                              } else {
                                validate23.errors = [
                                  {
                                    instancePath: instancePath + "/timestamp",
                                    schemaPath: "#/properties/timestamp/type",
                                    keyword: "type",
                                    params: { type: "string" },
                                    message: "must be string",
                                  },
                                ];
                                return false;
                              }
                            }
                          }
                          var valid0 = _errs72 === errors;
                        } else {
                          var valid0 = true;
                        }
                        if (valid0) {
                          if (data.tools !== void 0) {
                            let data25 = data.tools;
                            const _errs74 = errors;
                            if (errors === _errs74) {
                              if (Array.isArray(data25)) {
                                var valid12 = true;
                                const len3 = data25.length;
                                for (let i3 = 0; i3 < len3; i3++) {
                                  let data26 = data25[i3];
                                  const _errs76 = errors;
                                  if (errors === _errs76) {
                                    if (
                                      data26 &&
                                      typeof data26 == "object" &&
                                      !Array.isArray(data26)
                                    ) {
                                    } else {
                                      validate23.errors = [
                                        {
                                          instancePath:
                                            instancePath + "/tools/" + i3,
                                          schemaPath:
                                            "#/properties/tools/items/type",
                                          keyword: "type",
                                          params: { type: "object" },
                                          message: "must be object",
                                        },
                                      ];
                                      return false;
                                    }
                                  }
                                  var valid12 = _errs76 === errors;
                                  if (!valid12) {
                                    break;
                                  }
                                }
                              } else {
                                validate23.errors = [
                                  {
                                    instancePath: instancePath + "/tools",
                                    schemaPath: "#/properties/tools/type",
                                    keyword: "type",
                                    params: { type: "array" },
                                    message: "must be array",
                                  },
                                ];
                                return false;
                              }
                            }
                            var valid0 = _errs74 === errors;
                          } else {
                            var valid0 = true;
                          }
                          if (valid0) {
                            if (data.version !== void 0) {
                              let data27 = data.version;
                              const _errs79 = errors;
                              if (
                                !(
                                  typeof data27 == "number" &&
                                  !(data27 % 1) &&
                                  !isNaN(data27)
                                )
                              ) {
                                validate23.errors = [
                                  {
                                    instancePath: instancePath + "/version",
                                    schemaPath: "#/properties/version/type",
                                    keyword: "type",
                                    params: { type: "integer" },
                                    message: "must be integer",
                                  },
                                ];
                                return false;
                              }
                              if (1 !== data27) {
                                validate23.errors = [
                                  {
                                    instancePath: instancePath + "/version",
                                    schemaPath: "#/properties/version/const",
                                    keyword: "const",
                                    params: { allowedValue: 1 },
                                    message: "must be equal to constant",
                                  },
                                ];
                                return false;
                              }
                              var valid0 = _errs79 === errors;
                            } else {
                              var valid0 = true;
                            }
                            if (valid0) {
                              if (data.views !== void 0) {
                                let data28 = data.views;
                                const _errs81 = errors;
                                if (errors === _errs81) {
                                  if (Array.isArray(data28)) {
                                    var valid13 = true;
                                    const len4 = data28.length;
                                    for (let i4 = 0; i4 < len4; i4++) {
                                      let data29 = data28[i4];
                                      const _errs83 = errors;
                                      if (errors === _errs83) {
                                        if (
                                          data29 &&
                                          typeof data29 == "object" &&
                                          !Array.isArray(data29)
                                        ) {
                                        } else {
                                          validate23.errors = [
                                            {
                                              instancePath:
                                                instancePath + "/views/" + i4,
                                              schemaPath:
                                                "#/properties/views/items/type",
                                              keyword: "type",
                                              params: { type: "object" },
                                              message: "must be object",
                                            },
                                          ];
                                          return false;
                                        }
                                      }
                                      var valid13 = _errs83 === errors;
                                      if (!valid13) {
                                        break;
                                      }
                                    }
                                  } else {
                                    validate23.errors = [
                                      {
                                        instancePath: instancePath + "/views",
                                        schemaPath: "#/properties/views/type",
                                        keyword: "type",
                                        params: { type: "array" },
                                        message: "must be array",
                                      },
                                    ];
                                    return false;
                                  }
                                }
                                var valid0 = _errs81 === errors;
                              } else {
                                var valid0 = true;
                              }
                              if (valid0) {
                                if (data.weather !== void 0) {
                                  let data30 = data.weather;
                                  const _errs86 = errors;
                                  if (errors === _errs86) {
                                    if (Array.isArray(data30)) {
                                      var valid14 = true;
                                      const len5 = data30.length;
                                      for (let i5 = 0; i5 < len5; i5++) {
                                        const _errs88 = errors;
                                        if (
                                          !validate21(data30[i5], {
                                            instancePath:
                                              instancePath + "/weather/" + i5,
                                            parentData: data30,
                                            parentDataProperty: i5,
                                            rootData,
                                            dynamicAnchors,
                                          })
                                        ) {
                                          vErrors =
                                            vErrors === null
                                              ? validate21.errors
                                              : vErrors.concat(
                                                  validate21.errors,
                                                );
                                          errors = vErrors.length;
                                        }
                                        var valid14 = _errs88 === errors;
                                        if (!valid14) {
                                          break;
                                        }
                                      }
                                    } else {
                                      validate23.errors = [
                                        {
                                          instancePath:
                                            instancePath + "/weather",
                                          schemaPath:
                                            "#/properties/weather/type",
                                          keyword: "type",
                                          params: { type: "array" },
                                          message: "must be array",
                                        },
                                      ];
                                      return false;
                                    }
                                  }
                                  var valid0 = _errs86 === errors;
                                } else {
                                  var valid0 = true;
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        } else {
          validate23.errors = [
            {
              instancePath,
              schemaPath: "#/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            },
          ];
          return false;
        }
      }
      validate23.errors = vErrors;
      return errors === 0;
    }
    validate23.evaluated = {
      props: true,
      dynamicProps: false,
      dynamicItems: false,
    };
    var schema41 = {
      additionalProperties: false,
      properties: {
        device_id: {
          anyOf: [{ type: "string" }, { type: "null" }],
          title: "Device Id",
        },
        event_id: { title: "Event Id", type: "string" },
        payload: {
          additionalProperties: true,
          title: "Payload",
          type: "object",
        },
        resource_id: {
          anyOf: [{ type: "string" }, { type: "null" }],
          title: "Resource Id",
        },
        scope: { title: "Scope", type: "string" },
        sequence: { minimum: 1, title: "Sequence", type: "integer" },
        timestamp: { format: "date-time", title: "Timestamp", type: "string" },
        type: {
          enum: [
            "timer.created",
            "timer.updated",
            "timer.expired",
            "timer.acknowledged",
            "weather.updated",
            "home.entity_changed",
            "media.state_changed",
            "dashboard.show_view",
            "tool.execution_completed",
          ],
          title: "Type",
          type: "string",
        },
        version: { const: 1, default: 1, title: "Version", type: "integer" },
      },
      required: [
        "event_id",
        "timestamp",
        "sequence",
        "scope",
        "device_id",
        "type",
        "resource_id",
        "payload",
      ],
      title: "SemanticEvent",
      type: "object",
    };
    function validate26(
      data,
      {
        instancePath = "",
        parentData,
        parentDataProperty,
        rootData = data,
        dynamicAnchors = {},
      } = {},
    ) {
      let vErrors = null;
      let errors = 0;
      const evaluated0 = validate26.evaluated;
      if (evaluated0.dynamicProps) {
        evaluated0.props = void 0;
      }
      if (evaluated0.dynamicItems) {
        evaluated0.items = void 0;
      }
      if (errors === 0) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          let missing0;
          if (
            (data.cursor === void 0 && (missing0 = "cursor")) ||
            (data.events === void 0 && (missing0 = "events"))
          ) {
            validate26.errors = [
              {
                instancePath,
                schemaPath: "#/required",
                keyword: "required",
                params: { missingProperty: missing0 },
                message: "must have required property '" + missing0 + "'",
              },
            ];
            return false;
          } else {
            const _errs1 = errors;
            for (const key0 in data) {
              if (
                !(key0 === "cursor" || key0 === "events" || key0 === "version")
              ) {
                validate26.errors = [
                  {
                    instancePath,
                    schemaPath: "#/additionalProperties",
                    keyword: "additionalProperties",
                    params: { additionalProperty: key0 },
                    message: "must NOT have additional properties",
                  },
                ];
                return false;
                break;
              }
            }
            if (_errs1 === errors) {
              if (data.cursor !== void 0) {
                let data0 = data.cursor;
                const _errs2 = errors;
                if (
                  !(typeof data0 == "number" && !(data0 % 1) && !isNaN(data0))
                ) {
                  validate26.errors = [
                    {
                      instancePath: instancePath + "/cursor",
                      schemaPath: "#/properties/cursor/type",
                      keyword: "type",
                      params: { type: "integer" },
                      message: "must be integer",
                    },
                  ];
                  return false;
                }
                if (errors === _errs2) {
                  if (typeof data0 == "number") {
                    if (data0 < 0 || isNaN(data0)) {
                      validate26.errors = [
                        {
                          instancePath: instancePath + "/cursor",
                          schemaPath: "#/properties/cursor/minimum",
                          keyword: "minimum",
                          params: { comparison: ">=", limit: 0 },
                          message: "must be >= 0",
                        },
                      ];
                      return false;
                    }
                  }
                }
                var valid0 = _errs2 === errors;
              } else {
                var valid0 = true;
              }
              if (valid0) {
                if (data.events !== void 0) {
                  let data1 = data.events;
                  const _errs4 = errors;
                  if (errors === _errs4) {
                    if (Array.isArray(data1)) {
                      var valid1 = true;
                      const len0 = data1.length;
                      for (let i0 = 0; i0 < len0; i0++) {
                        let data2 = data1[i0];
                        const _errs6 = errors;
                        const _errs7 = errors;
                        if (errors === _errs7) {
                          if (
                            data2 &&
                            typeof data2 == "object" &&
                            !Array.isArray(data2)
                          ) {
                            let missing1;
                            if (
                              (data2.event_id === void 0 &&
                                (missing1 = "event_id")) ||
                              (data2.timestamp === void 0 &&
                                (missing1 = "timestamp")) ||
                              (data2.sequence === void 0 &&
                                (missing1 = "sequence")) ||
                              (data2.scope === void 0 &&
                                (missing1 = "scope")) ||
                              (data2.device_id === void 0 &&
                                (missing1 = "device_id")) ||
                              (data2.type === void 0 && (missing1 = "type")) ||
                              (data2.resource_id === void 0 &&
                                (missing1 = "resource_id")) ||
                              (data2.payload === void 0 &&
                                (missing1 = "payload"))
                            ) {
                              validate26.errors = [
                                {
                                  instancePath: instancePath + "/events/" + i0,
                                  schemaPath: "#/$defs/SemanticEvent/required",
                                  keyword: "required",
                                  params: { missingProperty: missing1 },
                                  message:
                                    "must have required property '" +
                                    missing1 +
                                    "'",
                                },
                              ];
                              return false;
                            } else {
                              const _errs9 = errors;
                              for (const key1 in data2) {
                                if (!func1.call(schema41.properties, key1)) {
                                  validate26.errors = [
                                    {
                                      instancePath:
                                        instancePath + "/events/" + i0,
                                      schemaPath:
                                        "#/$defs/SemanticEvent/additionalProperties",
                                      keyword: "additionalProperties",
                                      params: { additionalProperty: key1 },
                                      message:
                                        "must NOT have additional properties",
                                    },
                                  ];
                                  return false;
                                  break;
                                }
                              }
                              if (_errs9 === errors) {
                                if (data2.device_id !== void 0) {
                                  let data3 = data2.device_id;
                                  const _errs10 = errors;
                                  const _errs11 = errors;
                                  let valid4 = false;
                                  const _errs12 = errors;
                                  if (typeof data3 !== "string") {
                                    const err0 = {
                                      instancePath:
                                        instancePath +
                                        "/events/" +
                                        i0 +
                                        "/device_id",
                                      schemaPath:
                                        "#/$defs/SemanticEvent/properties/device_id/anyOf/0/type",
                                      keyword: "type",
                                      params: { type: "string" },
                                      message: "must be string",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err0];
                                    } else {
                                      vErrors.push(err0);
                                    }
                                    errors++;
                                  }
                                  var _valid0 = _errs12 === errors;
                                  valid4 = valid4 || _valid0;
                                  const _errs14 = errors;
                                  if (data3 !== null) {
                                    const err1 = {
                                      instancePath:
                                        instancePath +
                                        "/events/" +
                                        i0 +
                                        "/device_id",
                                      schemaPath:
                                        "#/$defs/SemanticEvent/properties/device_id/anyOf/1/type",
                                      keyword: "type",
                                      params: { type: "null" },
                                      message: "must be null",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err1];
                                    } else {
                                      vErrors.push(err1);
                                    }
                                    errors++;
                                  }
                                  var _valid0 = _errs14 === errors;
                                  valid4 = valid4 || _valid0;
                                  if (!valid4) {
                                    const err2 = {
                                      instancePath:
                                        instancePath +
                                        "/events/" +
                                        i0 +
                                        "/device_id",
                                      schemaPath:
                                        "#/$defs/SemanticEvent/properties/device_id/anyOf",
                                      keyword: "anyOf",
                                      params: {},
                                      message: "must match a schema in anyOf",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err2];
                                    } else {
                                      vErrors.push(err2);
                                    }
                                    errors++;
                                    validate26.errors = vErrors;
                                    return false;
                                  } else {
                                    errors = _errs11;
                                    if (vErrors !== null) {
                                      if (_errs11) {
                                        vErrors.length = _errs11;
                                      } else {
                                        vErrors = null;
                                      }
                                    }
                                  }
                                  var valid3 = _errs10 === errors;
                                } else {
                                  var valid3 = true;
                                }
                                if (valid3) {
                                  if (data2.event_id !== void 0) {
                                    const _errs16 = errors;
                                    if (typeof data2.event_id !== "string") {
                                      validate26.errors = [
                                        {
                                          instancePath:
                                            instancePath +
                                            "/events/" +
                                            i0 +
                                            "/event_id",
                                          schemaPath:
                                            "#/$defs/SemanticEvent/properties/event_id/type",
                                          keyword: "type",
                                          params: { type: "string" },
                                          message: "must be string",
                                        },
                                      ];
                                      return false;
                                    }
                                    var valid3 = _errs16 === errors;
                                  } else {
                                    var valid3 = true;
                                  }
                                  if (valid3) {
                                    if (data2.payload !== void 0) {
                                      let data5 = data2.payload;
                                      const _errs18 = errors;
                                      if (errors === _errs18) {
                                        if (
                                          data5 &&
                                          typeof data5 == "object" &&
                                          !Array.isArray(data5)
                                        ) {
                                        } else {
                                          validate26.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/events/" +
                                                i0 +
                                                "/payload",
                                              schemaPath:
                                                "#/$defs/SemanticEvent/properties/payload/type",
                                              keyword: "type",
                                              params: { type: "object" },
                                              message: "must be object",
                                            },
                                          ];
                                          return false;
                                        }
                                      }
                                      var valid3 = _errs18 === errors;
                                    } else {
                                      var valid3 = true;
                                    }
                                    if (valid3) {
                                      if (data2.resource_id !== void 0) {
                                        let data6 = data2.resource_id;
                                        const _errs21 = errors;
                                        const _errs22 = errors;
                                        let valid5 = false;
                                        const _errs23 = errors;
                                        if (typeof data6 !== "string") {
                                          const err3 = {
                                            instancePath:
                                              instancePath +
                                              "/events/" +
                                              i0 +
                                              "/resource_id",
                                            schemaPath:
                                              "#/$defs/SemanticEvent/properties/resource_id/anyOf/0/type",
                                            keyword: "type",
                                            params: { type: "string" },
                                            message: "must be string",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err3];
                                          } else {
                                            vErrors.push(err3);
                                          }
                                          errors++;
                                        }
                                        var _valid1 = _errs23 === errors;
                                        valid5 = valid5 || _valid1;
                                        const _errs25 = errors;
                                        if (data6 !== null) {
                                          const err4 = {
                                            instancePath:
                                              instancePath +
                                              "/events/" +
                                              i0 +
                                              "/resource_id",
                                            schemaPath:
                                              "#/$defs/SemanticEvent/properties/resource_id/anyOf/1/type",
                                            keyword: "type",
                                            params: { type: "null" },
                                            message: "must be null",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err4];
                                          } else {
                                            vErrors.push(err4);
                                          }
                                          errors++;
                                        }
                                        var _valid1 = _errs25 === errors;
                                        valid5 = valid5 || _valid1;
                                        if (!valid5) {
                                          const err5 = {
                                            instancePath:
                                              instancePath +
                                              "/events/" +
                                              i0 +
                                              "/resource_id",
                                            schemaPath:
                                              "#/$defs/SemanticEvent/properties/resource_id/anyOf",
                                            keyword: "anyOf",
                                            params: {},
                                            message:
                                              "must match a schema in anyOf",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err5];
                                          } else {
                                            vErrors.push(err5);
                                          }
                                          errors++;
                                          validate26.errors = vErrors;
                                          return false;
                                        } else {
                                          errors = _errs22;
                                          if (vErrors !== null) {
                                            if (_errs22) {
                                              vErrors.length = _errs22;
                                            } else {
                                              vErrors = null;
                                            }
                                          }
                                        }
                                        var valid3 = _errs21 === errors;
                                      } else {
                                        var valid3 = true;
                                      }
                                      if (valid3) {
                                        if (data2.scope !== void 0) {
                                          const _errs27 = errors;
                                          if (typeof data2.scope !== "string") {
                                            validate26.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/events/" +
                                                  i0 +
                                                  "/scope",
                                                schemaPath:
                                                  "#/$defs/SemanticEvent/properties/scope/type",
                                                keyword: "type",
                                                params: { type: "string" },
                                                message: "must be string",
                                              },
                                            ];
                                            return false;
                                          }
                                          var valid3 = _errs27 === errors;
                                        } else {
                                          var valid3 = true;
                                        }
                                        if (valid3) {
                                          if (data2.sequence !== void 0) {
                                            let data8 = data2.sequence;
                                            const _errs29 = errors;
                                            if (
                                              !(
                                                typeof data8 == "number" &&
                                                !(data8 % 1) &&
                                                !isNaN(data8)
                                              )
                                            ) {
                                              validate26.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/events/" +
                                                    i0 +
                                                    "/sequence",
                                                  schemaPath:
                                                    "#/$defs/SemanticEvent/properties/sequence/type",
                                                  keyword: "type",
                                                  params: { type: "integer" },
                                                  message: "must be integer",
                                                },
                                              ];
                                              return false;
                                            }
                                            if (errors === _errs29) {
                                              if (typeof data8 == "number") {
                                                if (data8 < 1 || isNaN(data8)) {
                                                  validate26.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/events/" +
                                                        i0 +
                                                        "/sequence",
                                                      schemaPath:
                                                        "#/$defs/SemanticEvent/properties/sequence/minimum",
                                                      keyword: "minimum",
                                                      params: {
                                                        comparison: ">=",
                                                        limit: 1,
                                                      },
                                                      message: "must be >= 1",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                              }
                                            }
                                            var valid3 = _errs29 === errors;
                                          } else {
                                            var valid3 = true;
                                          }
                                          if (valid3) {
                                            if (data2.timestamp !== void 0) {
                                              let data9 = data2.timestamp;
                                              const _errs31 = errors;
                                              if (errors === _errs31) {
                                                if (errors === _errs31) {
                                                  if (
                                                    typeof data9 === "string"
                                                  ) {
                                                    if (
                                                      !formats2.validate(data9)
                                                    ) {
                                                      validate26.errors = [
                                                        {
                                                          instancePath:
                                                            instancePath +
                                                            "/events/" +
                                                            i0 +
                                                            "/timestamp",
                                                          schemaPath:
                                                            "#/$defs/SemanticEvent/properties/timestamp/format",
                                                          keyword: "format",
                                                          params: {
                                                            format: "date-time",
                                                          },
                                                          message:
                                                            'must match format "date-time"',
                                                        },
                                                      ];
                                                      return false;
                                                    }
                                                  } else {
                                                    validate26.errors = [
                                                      {
                                                        instancePath:
                                                          instancePath +
                                                          "/events/" +
                                                          i0 +
                                                          "/timestamp",
                                                        schemaPath:
                                                          "#/$defs/SemanticEvent/properties/timestamp/type",
                                                        keyword: "type",
                                                        params: {
                                                          type: "string",
                                                        },
                                                        message:
                                                          "must be string",
                                                      },
                                                    ];
                                                    return false;
                                                  }
                                                }
                                              }
                                              var valid3 = _errs31 === errors;
                                            } else {
                                              var valid3 = true;
                                            }
                                            if (valid3) {
                                              if (data2.type !== void 0) {
                                                let data10 = data2.type;
                                                const _errs33 = errors;
                                                if (
                                                  typeof data10 !== "string"
                                                ) {
                                                  validate26.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/events/" +
                                                        i0 +
                                                        "/type",
                                                      schemaPath:
                                                        "#/$defs/SemanticEvent/properties/type/type",
                                                      keyword: "type",
                                                      params: {
                                                        type: "string",
                                                      },
                                                      message: "must be string",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                                if (
                                                  !(
                                                    data10 ===
                                                      "timer.created" ||
                                                    data10 ===
                                                      "timer.updated" ||
                                                    data10 ===
                                                      "timer.expired" ||
                                                    data10 ===
                                                      "timer.acknowledged" ||
                                                    data10 ===
                                                      "weather.updated" ||
                                                    data10 ===
                                                      "home.entity_changed" ||
                                                    data10 ===
                                                      "media.state_changed" ||
                                                    data10 ===
                                                      "dashboard.show_view" ||
                                                    data10 ===
                                                      "tool.execution_completed"
                                                  )
                                                ) {
                                                  validate26.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/events/" +
                                                        i0 +
                                                        "/type",
                                                      schemaPath:
                                                        "#/$defs/SemanticEvent/properties/type/enum",
                                                      keyword: "enum",
                                                      params: {
                                                        allowedValues:
                                                          schema41.properties
                                                            .type.enum,
                                                      },
                                                      message:
                                                        "must be equal to one of the allowed values",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                                var valid3 = _errs33 === errors;
                                              } else {
                                                var valid3 = true;
                                              }
                                              if (valid3) {
                                                if (data2.version !== void 0) {
                                                  let data11 = data2.version;
                                                  const _errs35 = errors;
                                                  if (
                                                    !(
                                                      typeof data11 ==
                                                        "number" &&
                                                      !(data11 % 1) &&
                                                      !isNaN(data11)
                                                    )
                                                  ) {
                                                    validate26.errors = [
                                                      {
                                                        instancePath:
                                                          instancePath +
                                                          "/events/" +
                                                          i0 +
                                                          "/version",
                                                        schemaPath:
                                                          "#/$defs/SemanticEvent/properties/version/type",
                                                        keyword: "type",
                                                        params: {
                                                          type: "integer",
                                                        },
                                                        message:
                                                          "must be integer",
                                                      },
                                                    ];
                                                    return false;
                                                  }
                                                  if (1 !== data11) {
                                                    validate26.errors = [
                                                      {
                                                        instancePath:
                                                          instancePath +
                                                          "/events/" +
                                                          i0 +
                                                          "/version",
                                                        schemaPath:
                                                          "#/$defs/SemanticEvent/properties/version/const",
                                                        keyword: "const",
                                                        params: {
                                                          allowedValue: 1,
                                                        },
                                                        message:
                                                          "must be equal to constant",
                                                      },
                                                    ];
                                                    return false;
                                                  }
                                                  var valid3 =
                                                    _errs35 === errors;
                                                } else {
                                                  var valid3 = true;
                                                }
                                              }
                                            }
                                          }
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                            }
                          } else {
                            validate26.errors = [
                              {
                                instancePath: instancePath + "/events/" + i0,
                                schemaPath: "#/$defs/SemanticEvent/type",
                                keyword: "type",
                                params: { type: "object" },
                                message: "must be object",
                              },
                            ];
                            return false;
                          }
                        }
                        var valid1 = _errs6 === errors;
                        if (!valid1) {
                          break;
                        }
                      }
                    } else {
                      validate26.errors = [
                        {
                          instancePath: instancePath + "/events",
                          schemaPath: "#/properties/events/type",
                          keyword: "type",
                          params: { type: "array" },
                          message: "must be array",
                        },
                      ];
                      return false;
                    }
                  }
                  var valid0 = _errs4 === errors;
                } else {
                  var valid0 = true;
                }
                if (valid0) {
                  if (data.version !== void 0) {
                    let data12 = data.version;
                    const _errs37 = errors;
                    if (
                      !(
                        typeof data12 == "number" &&
                        !(data12 % 1) &&
                        !isNaN(data12)
                      )
                    ) {
                      validate26.errors = [
                        {
                          instancePath: instancePath + "/version",
                          schemaPath: "#/properties/version/type",
                          keyword: "type",
                          params: { type: "integer" },
                          message: "must be integer",
                        },
                      ];
                      return false;
                    }
                    if (1 !== data12) {
                      validate26.errors = [
                        {
                          instancePath: instancePath + "/version",
                          schemaPath: "#/properties/version/const",
                          keyword: "const",
                          params: { allowedValue: 1 },
                          message: "must be equal to constant",
                        },
                      ];
                      return false;
                    }
                    var valid0 = _errs37 === errors;
                  } else {
                    var valid0 = true;
                  }
                }
              }
            }
          }
        } else {
          validate26.errors = [
            {
              instancePath,
              schemaPath: "#/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            },
          ];
          return false;
        }
      }
      validate26.errors = vErrors;
      return errors === 0;
    }
    validate26.evaluated = {
      props: true,
      dynamicProps: false,
      dynamicItems: false,
    };
    function validate28(
      data,
      {
        instancePath = "",
        parentData,
        parentDataProperty,
        rootData = data,
        dynamicAnchors = {},
      } = {},
    ) {
      let vErrors = null;
      let errors = 0;
      const evaluated0 = validate28.evaluated;
      if (evaluated0.dynamicProps) {
        evaluated0.props = void 0;
      }
      if (evaluated0.dynamicItems) {
        evaluated0.items = void 0;
      }
      if (errors === 0) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          let missing0;
          if (
            (data.id === void 0 && (missing0 = "id")) ||
            (data.device_id === void 0 && (missing0 = "device_id")) ||
            (data.name === void 0 && (missing0 = "name")) ||
            (data.expires_at === void 0 && (missing0 = "expires_at")) ||
            (data.csrf === void 0 && (missing0 = "csrf")) ||
            (data.permissions === void 0 && (missing0 = "permissions"))
          ) {
            validate28.errors = [
              {
                instancePath,
                schemaPath: "#/required",
                keyword: "required",
                params: { missingProperty: missing0 },
                message: "must have required property '" + missing0 + "'",
              },
            ];
            return false;
          } else {
            const _errs1 = errors;
            for (const key0 in data) {
              if (
                !(
                  key0 === "csrf" ||
                  key0 === "device_id" ||
                  key0 === "expires_at" ||
                  key0 === "id" ||
                  key0 === "name" ||
                  key0 === "permissions"
                )
              ) {
                validate28.errors = [
                  {
                    instancePath,
                    schemaPath: "#/additionalProperties",
                    keyword: "additionalProperties",
                    params: { additionalProperty: key0 },
                    message: "must NOT have additional properties",
                  },
                ];
                return false;
                break;
              }
            }
            if (_errs1 === errors) {
              if (data.csrf !== void 0) {
                const _errs2 = errors;
                if (typeof data.csrf !== "string") {
                  validate28.errors = [
                    {
                      instancePath: instancePath + "/csrf",
                      schemaPath: "#/properties/csrf/type",
                      keyword: "type",
                      params: { type: "string" },
                      message: "must be string",
                    },
                  ];
                  return false;
                }
                var valid0 = _errs2 === errors;
              } else {
                var valid0 = true;
              }
              if (valid0) {
                if (data.device_id !== void 0) {
                  let data1 = data.device_id;
                  const _errs4 = errors;
                  if (errors === _errs4) {
                    if (typeof data1 === "string") {
                      if (func2(data1) > 64) {
                        validate28.errors = [
                          {
                            instancePath: instancePath + "/device_id",
                            schemaPath: "#/properties/device_id/maxLength",
                            keyword: "maxLength",
                            params: { limit: 64 },
                            message: "must NOT have more than 64 characters",
                          },
                        ];
                        return false;
                      } else {
                        if (func2(data1) < 1) {
                          validate28.errors = [
                            {
                              instancePath: instancePath + "/device_id",
                              schemaPath: "#/properties/device_id/minLength",
                              keyword: "minLength",
                              params: { limit: 1 },
                              message: "must NOT have fewer than 1 characters",
                            },
                          ];
                          return false;
                        } else {
                          if (!pattern4.test(data1)) {
                            validate28.errors = [
                              {
                                instancePath: instancePath + "/device_id",
                                schemaPath: "#/properties/device_id/pattern",
                                keyword: "pattern",
                                params: { pattern: "^[a-zA-Z0-9_-]+$" },
                                message:
                                  'must match pattern "^[a-zA-Z0-9_-]+$"',
                              },
                            ];
                            return false;
                          }
                        }
                      }
                    } else {
                      validate28.errors = [
                        {
                          instancePath: instancePath + "/device_id",
                          schemaPath: "#/properties/device_id/type",
                          keyword: "type",
                          params: { type: "string" },
                          message: "must be string",
                        },
                      ];
                      return false;
                    }
                  }
                  var valid0 = _errs4 === errors;
                } else {
                  var valid0 = true;
                }
                if (valid0) {
                  if (data.expires_at !== void 0) {
                    const _errs6 = errors;
                    if (typeof data.expires_at !== "string") {
                      validate28.errors = [
                        {
                          instancePath: instancePath + "/expires_at",
                          schemaPath: "#/properties/expires_at/type",
                          keyword: "type",
                          params: { type: "string" },
                          message: "must be string",
                        },
                      ];
                      return false;
                    }
                    var valid0 = _errs6 === errors;
                  } else {
                    var valid0 = true;
                  }
                  if (valid0) {
                    if (data.id !== void 0) {
                      let data3 = data.id;
                      const _errs8 = errors;
                      if (errors === _errs8) {
                        if (errors === _errs8) {
                          if (typeof data3 === "string") {
                            if (!formats0.test(data3)) {
                              validate28.errors = [
                                {
                                  instancePath: instancePath + "/id",
                                  schemaPath: "#/properties/id/format",
                                  keyword: "format",
                                  params: { format: "uuid" },
                                  message: 'must match format "uuid"',
                                },
                              ];
                              return false;
                            }
                          } else {
                            validate28.errors = [
                              {
                                instancePath: instancePath + "/id",
                                schemaPath: "#/properties/id/type",
                                keyword: "type",
                                params: { type: "string" },
                                message: "must be string",
                              },
                            ];
                            return false;
                          }
                        }
                      }
                      var valid0 = _errs8 === errors;
                    } else {
                      var valid0 = true;
                    }
                    if (valid0) {
                      if (data.name !== void 0) {
                        const _errs10 = errors;
                        if (typeof data.name !== "string") {
                          validate28.errors = [
                            {
                              instancePath: instancePath + "/name",
                              schemaPath: "#/properties/name/type",
                              keyword: "type",
                              params: { type: "string" },
                              message: "must be string",
                            },
                          ];
                          return false;
                        }
                        var valid0 = _errs10 === errors;
                      } else {
                        var valid0 = true;
                      }
                      if (valid0) {
                        if (data.permissions !== void 0) {
                          let data5 = data.permissions;
                          const _errs12 = errors;
                          const _errs13 = errors;
                          if (errors === _errs13) {
                            if (
                              data5 &&
                              typeof data5 == "object" &&
                              !Array.isArray(data5)
                            ) {
                              const _errs15 = errors;
                              for (const key1 in data5) {
                                if (
                                  !(
                                    key1 === "captions" ||
                                    key1 === "debug" ||
                                    key1 === "home_control" ||
                                    key1 === "home_entities" ||
                                    key1 === "timers" ||
                                    key1 === "voice_control"
                                  )
                                ) {
                                  validate28.errors = [
                                    {
                                      instancePath:
                                        instancePath + "/permissions",
                                      schemaPath:
                                        "#/$defs/BrowserGrant/additionalProperties",
                                      keyword: "additionalProperties",
                                      params: { additionalProperty: key1 },
                                      message:
                                        "must NOT have additional properties",
                                    },
                                  ];
                                  return false;
                                  break;
                                }
                              }
                              if (_errs15 === errors) {
                                if (data5.captions !== void 0) {
                                  const _errs16 = errors;
                                  if (typeof data5.captions !== "boolean") {
                                    validate28.errors = [
                                      {
                                        instancePath:
                                          instancePath +
                                          "/permissions/captions",
                                        schemaPath:
                                          "#/$defs/BrowserGrant/properties/captions/type",
                                        keyword: "type",
                                        params: { type: "boolean" },
                                        message: "must be boolean",
                                      },
                                    ];
                                    return false;
                                  }
                                  var valid2 = _errs16 === errors;
                                } else {
                                  var valid2 = true;
                                }
                                if (valid2) {
                                  if (data5.debug !== void 0) {
                                    const _errs18 = errors;
                                    if (typeof data5.debug !== "boolean") {
                                      validate28.errors = [
                                        {
                                          instancePath:
                                            instancePath + "/permissions/debug",
                                          schemaPath:
                                            "#/$defs/BrowserGrant/properties/debug/type",
                                          keyword: "type",
                                          params: { type: "boolean" },
                                          message: "must be boolean",
                                        },
                                      ];
                                      return false;
                                    }
                                    var valid2 = _errs18 === errors;
                                  } else {
                                    var valid2 = true;
                                  }
                                  if (valid2) {
                                    if (data5.home_control !== void 0) {
                                      const _errs20 = errors;
                                      if (
                                        typeof data5.home_control !== "boolean"
                                      ) {
                                        validate28.errors = [
                                          {
                                            instancePath:
                                              instancePath +
                                              "/permissions/home_control",
                                            schemaPath:
                                              "#/$defs/BrowserGrant/properties/home_control/type",
                                            keyword: "type",
                                            params: { type: "boolean" },
                                            message: "must be boolean",
                                          },
                                        ];
                                        return false;
                                      }
                                      var valid2 = _errs20 === errors;
                                    } else {
                                      var valid2 = true;
                                    }
                                    if (valid2) {
                                      if (data5.home_entities !== void 0) {
                                        let data9 = data5.home_entities;
                                        const _errs22 = errors;
                                        if (errors === _errs22) {
                                          if (Array.isArray(data9)) {
                                            var valid3 = true;
                                            const len0 = data9.length;
                                            for (let i0 = 0; i0 < len0; i0++) {
                                              const _errs24 = errors;
                                              if (
                                                typeof data9[i0] !== "string"
                                              ) {
                                                validate28.errors = [
                                                  {
                                                    instancePath:
                                                      instancePath +
                                                      "/permissions/home_entities/" +
                                                      i0,
                                                    schemaPath:
                                                      "#/$defs/BrowserGrant/properties/home_entities/items/type",
                                                    keyword: "type",
                                                    params: { type: "string" },
                                                    message: "must be string",
                                                  },
                                                ];
                                                return false;
                                              }
                                              var valid3 = _errs24 === errors;
                                              if (!valid3) {
                                                break;
                                              }
                                            }
                                            if (valid3) {
                                              let i1 = data9.length;
                                              let j0;
                                              if (i1 > 1) {
                                                const indices0 = {};
                                                for (; i1--; ) {
                                                  let item0 = data9[i1];
                                                  if (
                                                    typeof item0 !== "string"
                                                  ) {
                                                    continue;
                                                  }
                                                  if (
                                                    typeof indices0[item0] ==
                                                    "number"
                                                  ) {
                                                    j0 = indices0[item0];
                                                    validate28.errors = [
                                                      {
                                                        instancePath:
                                                          instancePath +
                                                          "/permissions/home_entities",
                                                        schemaPath:
                                                          "#/$defs/BrowserGrant/properties/home_entities/uniqueItems",
                                                        keyword: "uniqueItems",
                                                        params: {
                                                          i: i1,
                                                          j: j0,
                                                        },
                                                        message:
                                                          "must NOT have duplicate items (items ## " +
                                                          j0 +
                                                          " and " +
                                                          i1 +
                                                          " are identical)",
                                                      },
                                                    ];
                                                    return false;
                                                    break;
                                                  }
                                                  indices0[item0] = i1;
                                                }
                                              }
                                            }
                                          } else {
                                            validate28.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/permissions/home_entities",
                                                schemaPath:
                                                  "#/$defs/BrowserGrant/properties/home_entities/type",
                                                keyword: "type",
                                                params: { type: "array" },
                                                message: "must be array",
                                              },
                                            ];
                                            return false;
                                          }
                                        }
                                        var valid2 = _errs22 === errors;
                                      } else {
                                        var valid2 = true;
                                      }
                                      if (valid2) {
                                        if (data5.timers !== void 0) {
                                          const _errs26 = errors;
                                          if (
                                            typeof data5.timers !== "boolean"
                                          ) {
                                            validate28.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/permissions/timers",
                                                schemaPath:
                                                  "#/$defs/BrowserGrant/properties/timers/type",
                                                keyword: "type",
                                                params: { type: "boolean" },
                                                message: "must be boolean",
                                              },
                                            ];
                                            return false;
                                          }
                                          var valid2 = _errs26 === errors;
                                        } else {
                                          var valid2 = true;
                                        }
                                        if (valid2) {
                                          if (data5.voice_control !== void 0) {
                                            const _errs28 = errors;
                                            if (
                                              typeof data5.voice_control !==
                                              "boolean"
                                            ) {
                                              validate28.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/permissions/voice_control",
                                                  schemaPath:
                                                    "#/$defs/BrowserGrant/properties/voice_control/type",
                                                  keyword: "type",
                                                  params: { type: "boolean" },
                                                  message: "must be boolean",
                                                },
                                              ];
                                              return false;
                                            }
                                            var valid2 = _errs28 === errors;
                                          } else {
                                            var valid2 = true;
                                          }
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                            } else {
                              validate28.errors = [
                                {
                                  instancePath: instancePath + "/permissions",
                                  schemaPath: "#/$defs/BrowserGrant/type",
                                  keyword: "type",
                                  params: { type: "object" },
                                  message: "must be object",
                                },
                              ];
                              return false;
                            }
                          }
                          var valid0 = _errs12 === errors;
                        } else {
                          var valid0 = true;
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        } else {
          validate28.errors = [
            {
              instancePath,
              schemaPath: "#/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            },
          ];
          return false;
        }
      }
      validate28.errors = vErrors;
      return errors === 0;
    }
    validate28.evaluated = {
      props: true,
      dynamicProps: false,
      dynamicItems: false,
    };
    var schema50 = {
      additionalProperties: false,
      properties: {
        device_id: {
          maxLength: 64,
          minLength: 1,
          pattern: "^[a-zA-Z0-9_-]+$",
          title: "Device Id",
          type: "string",
        },
        event_id: { format: "uuid", title: "Event Id", type: "string" },
        payload: {
          additionalProperties: true,
          title: "Payload",
          type: "object",
        },
        revision: { minimum: 1, title: "Revision", type: "integer" },
        timestamp: { format: "date-time", title: "Timestamp", type: "string" },
        type: {
          enum: [
            "assistant.transcribing",
            "assistant.thinking",
            "assistant.tool_executing",
            "assistant.synthesizing",
            "assistant.delivering",
            "assistant.speaking",
            "assistant.follow_up",
            "assistant.error",
            "assistant.edge_state",
            "assistant.playback",
          ],
          title: "Type",
          type: "string",
        },
        version: { const: 1, title: "Version", type: "integer" },
      },
      required: [
        "version",
        "event_id",
        "revision",
        "timestamp",
        "device_id",
        "type",
        "payload",
      ],
      title: "VoiceEvent",
      type: "object",
    };
    var schema47 = {
      additionalProperties: false,
      properties: {
        alarm_id: { format: "uuid", title: "Alarm Id", type: "string" },
        delivery_status: {
          enum: [
            "pending",
            "delivered",
            "started",
            "completed",
            "cancelled",
            "failed",
            "indeterminate",
          ],
          title: "Delivery Status",
          type: "string",
        },
        device_id: {
          maxLength: 64,
          minLength: 1,
          pattern: "^[a-zA-Z0-9_-]+$",
          title: "Device Id",
          type: "string",
        },
        pending: { title: "Pending", type: "boolean" },
        updated_at: {
          anyOf: [{ format: "date-time", type: "string" }, { type: "null" }],
          title: "Updated At",
        },
      },
      required: [
        "alarm_id",
        "device_id",
        "delivery_status",
        "updated_at",
        "pending",
      ],
      title: "AlarmDeliveryState",
      type: "object",
    };
    function validate31(
      data,
      {
        instancePath = "",
        parentData,
        parentDataProperty,
        rootData = data,
        dynamicAnchors = {},
      } = {},
    ) {
      let vErrors = null;
      let errors = 0;
      const evaluated0 = validate31.evaluated;
      if (evaluated0.dynamicProps) {
        evaluated0.props = void 0;
      }
      if (evaluated0.dynamicItems) {
        evaluated0.items = void 0;
      }
      if (errors === 0) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          if (data.alarms !== void 0) {
            let data0 = data.alarms;
            const _errs1 = errors;
            if (errors === _errs1) {
              if (Array.isArray(data0)) {
                var valid1 = true;
                const len0 = data0.length;
                for (let i0 = 0; i0 < len0; i0++) {
                  let data1 = data0[i0];
                  const _errs3 = errors;
                  const _errs4 = errors;
                  if (errors === _errs4) {
                    if (
                      data1 &&
                      typeof data1 == "object" &&
                      !Array.isArray(data1)
                    ) {
                      let missing0;
                      if (
                        (data1.alarm_id === void 0 &&
                          (missing0 = "alarm_id")) ||
                        (data1.device_id === void 0 &&
                          (missing0 = "device_id")) ||
                        (data1.delivery_status === void 0 &&
                          (missing0 = "delivery_status")) ||
                        (data1.updated_at === void 0 &&
                          (missing0 = "updated_at")) ||
                        (data1.pending === void 0 && (missing0 = "pending"))
                      ) {
                        validate31.errors = [
                          {
                            instancePath: instancePath + "/alarms/" + i0,
                            schemaPath: "#/$defs/AlarmDeliveryState/required",
                            keyword: "required",
                            params: { missingProperty: missing0 },
                            message:
                              "must have required property '" + missing0 + "'",
                          },
                        ];
                        return false;
                      } else {
                        const _errs6 = errors;
                        for (const key0 in data1) {
                          if (
                            !(
                              key0 === "alarm_id" ||
                              key0 === "delivery_status" ||
                              key0 === "device_id" ||
                              key0 === "pending" ||
                              key0 === "updated_at"
                            )
                          ) {
                            validate31.errors = [
                              {
                                instancePath: instancePath + "/alarms/" + i0,
                                schemaPath:
                                  "#/$defs/AlarmDeliveryState/additionalProperties",
                                keyword: "additionalProperties",
                                params: { additionalProperty: key0 },
                                message: "must NOT have additional properties",
                              },
                            ];
                            return false;
                            break;
                          }
                        }
                        if (_errs6 === errors) {
                          if (data1.alarm_id !== void 0) {
                            let data2 = data1.alarm_id;
                            const _errs7 = errors;
                            if (errors === _errs7) {
                              if (errors === _errs7) {
                                if (typeof data2 === "string") {
                                  if (!formats0.test(data2)) {
                                    validate31.errors = [
                                      {
                                        instancePath:
                                          instancePath +
                                          "/alarms/" +
                                          i0 +
                                          "/alarm_id",
                                        schemaPath:
                                          "#/$defs/AlarmDeliveryState/properties/alarm_id/format",
                                        keyword: "format",
                                        params: { format: "uuid" },
                                        message: 'must match format "uuid"',
                                      },
                                    ];
                                    return false;
                                  }
                                } else {
                                  validate31.errors = [
                                    {
                                      instancePath:
                                        instancePath +
                                        "/alarms/" +
                                        i0 +
                                        "/alarm_id",
                                      schemaPath:
                                        "#/$defs/AlarmDeliveryState/properties/alarm_id/type",
                                      keyword: "type",
                                      params: { type: "string" },
                                      message: "must be string",
                                    },
                                  ];
                                  return false;
                                }
                              }
                            }
                            var valid3 = _errs7 === errors;
                          } else {
                            var valid3 = true;
                          }
                          if (valid3) {
                            if (data1.delivery_status !== void 0) {
                              let data3 = data1.delivery_status;
                              const _errs9 = errors;
                              if (typeof data3 !== "string") {
                                validate31.errors = [
                                  {
                                    instancePath:
                                      instancePath +
                                      "/alarms/" +
                                      i0 +
                                      "/delivery_status",
                                    schemaPath:
                                      "#/$defs/AlarmDeliveryState/properties/delivery_status/type",
                                    keyword: "type",
                                    params: { type: "string" },
                                    message: "must be string",
                                  },
                                ];
                                return false;
                              }
                              if (
                                !(
                                  data3 === "pending" ||
                                  data3 === "delivered" ||
                                  data3 === "started" ||
                                  data3 === "completed" ||
                                  data3 === "cancelled" ||
                                  data3 === "failed" ||
                                  data3 === "indeterminate"
                                )
                              ) {
                                validate31.errors = [
                                  {
                                    instancePath:
                                      instancePath +
                                      "/alarms/" +
                                      i0 +
                                      "/delivery_status",
                                    schemaPath:
                                      "#/$defs/AlarmDeliveryState/properties/delivery_status/enum",
                                    keyword: "enum",
                                    params: {
                                      allowedValues:
                                        schema47.properties.delivery_status
                                          .enum,
                                    },
                                    message:
                                      "must be equal to one of the allowed values",
                                  },
                                ];
                                return false;
                              }
                              var valid3 = _errs9 === errors;
                            } else {
                              var valid3 = true;
                            }
                            if (valid3) {
                              if (data1.device_id !== void 0) {
                                let data4 = data1.device_id;
                                const _errs11 = errors;
                                if (errors === _errs11) {
                                  if (typeof data4 === "string") {
                                    if (func2(data4) > 64) {
                                      validate31.errors = [
                                        {
                                          instancePath:
                                            instancePath +
                                            "/alarms/" +
                                            i0 +
                                            "/device_id",
                                          schemaPath:
                                            "#/$defs/AlarmDeliveryState/properties/device_id/maxLength",
                                          keyword: "maxLength",
                                          params: { limit: 64 },
                                          message:
                                            "must NOT have more than 64 characters",
                                        },
                                      ];
                                      return false;
                                    } else {
                                      if (func2(data4) < 1) {
                                        validate31.errors = [
                                          {
                                            instancePath:
                                              instancePath +
                                              "/alarms/" +
                                              i0 +
                                              "/device_id",
                                            schemaPath:
                                              "#/$defs/AlarmDeliveryState/properties/device_id/minLength",
                                            keyword: "minLength",
                                            params: { limit: 1 },
                                            message:
                                              "must NOT have fewer than 1 characters",
                                          },
                                        ];
                                        return false;
                                      } else {
                                        if (!pattern4.test(data4)) {
                                          validate31.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/alarms/" +
                                                i0 +
                                                "/device_id",
                                              schemaPath:
                                                "#/$defs/AlarmDeliveryState/properties/device_id/pattern",
                                              keyword: "pattern",
                                              params: {
                                                pattern: "^[a-zA-Z0-9_-]+$",
                                              },
                                              message:
                                                'must match pattern "^[a-zA-Z0-9_-]+$"',
                                            },
                                          ];
                                          return false;
                                        }
                                      }
                                    }
                                  } else {
                                    validate31.errors = [
                                      {
                                        instancePath:
                                          instancePath +
                                          "/alarms/" +
                                          i0 +
                                          "/device_id",
                                        schemaPath:
                                          "#/$defs/AlarmDeliveryState/properties/device_id/type",
                                        keyword: "type",
                                        params: { type: "string" },
                                        message: "must be string",
                                      },
                                    ];
                                    return false;
                                  }
                                }
                                var valid3 = _errs11 === errors;
                              } else {
                                var valid3 = true;
                              }
                              if (valid3) {
                                if (data1.pending !== void 0) {
                                  const _errs13 = errors;
                                  if (typeof data1.pending !== "boolean") {
                                    validate31.errors = [
                                      {
                                        instancePath:
                                          instancePath +
                                          "/alarms/" +
                                          i0 +
                                          "/pending",
                                        schemaPath:
                                          "#/$defs/AlarmDeliveryState/properties/pending/type",
                                        keyword: "type",
                                        params: { type: "boolean" },
                                        message: "must be boolean",
                                      },
                                    ];
                                    return false;
                                  }
                                  var valid3 = _errs13 === errors;
                                } else {
                                  var valid3 = true;
                                }
                                if (valid3) {
                                  if (data1.updated_at !== void 0) {
                                    let data6 = data1.updated_at;
                                    const _errs15 = errors;
                                    const _errs16 = errors;
                                    let valid4 = false;
                                    const _errs17 = errors;
                                    if (errors === _errs17) {
                                      if (errors === _errs17) {
                                        if (typeof data6 === "string") {
                                          if (!formats2.validate(data6)) {
                                            const err0 = {
                                              instancePath:
                                                instancePath +
                                                "/alarms/" +
                                                i0 +
                                                "/updated_at",
                                              schemaPath:
                                                "#/$defs/AlarmDeliveryState/properties/updated_at/anyOf/0/format",
                                              keyword: "format",
                                              params: { format: "date-time" },
                                              message:
                                                'must match format "date-time"',
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err0];
                                            } else {
                                              vErrors.push(err0);
                                            }
                                            errors++;
                                          }
                                        } else {
                                          const err1 = {
                                            instancePath:
                                              instancePath +
                                              "/alarms/" +
                                              i0 +
                                              "/updated_at",
                                            schemaPath:
                                              "#/$defs/AlarmDeliveryState/properties/updated_at/anyOf/0/type",
                                            keyword: "type",
                                            params: { type: "string" },
                                            message: "must be string",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err1];
                                          } else {
                                            vErrors.push(err1);
                                          }
                                          errors++;
                                        }
                                      }
                                    }
                                    var _valid0 = _errs17 === errors;
                                    valid4 = valid4 || _valid0;
                                    const _errs19 = errors;
                                    if (data6 !== null) {
                                      const err2 = {
                                        instancePath:
                                          instancePath +
                                          "/alarms/" +
                                          i0 +
                                          "/updated_at",
                                        schemaPath:
                                          "#/$defs/AlarmDeliveryState/properties/updated_at/anyOf/1/type",
                                        keyword: "type",
                                        params: { type: "null" },
                                        message: "must be null",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err2];
                                      } else {
                                        vErrors.push(err2);
                                      }
                                      errors++;
                                    }
                                    var _valid0 = _errs19 === errors;
                                    valid4 = valid4 || _valid0;
                                    if (!valid4) {
                                      const err3 = {
                                        instancePath:
                                          instancePath +
                                          "/alarms/" +
                                          i0 +
                                          "/updated_at",
                                        schemaPath:
                                          "#/$defs/AlarmDeliveryState/properties/updated_at/anyOf",
                                        keyword: "anyOf",
                                        params: {},
                                        message: "must match a schema in anyOf",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err3];
                                      } else {
                                        vErrors.push(err3);
                                      }
                                      errors++;
                                      validate31.errors = vErrors;
                                      return false;
                                    } else {
                                      errors = _errs16;
                                      if (vErrors !== null) {
                                        if (_errs16) {
                                          vErrors.length = _errs16;
                                        } else {
                                          vErrors = null;
                                        }
                                      }
                                    }
                                    var valid3 = _errs15 === errors;
                                  } else {
                                    var valid3 = true;
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    } else {
                      validate31.errors = [
                        {
                          instancePath: instancePath + "/alarms/" + i0,
                          schemaPath: "#/$defs/AlarmDeliveryState/type",
                          keyword: "type",
                          params: { type: "object" },
                          message: "must be object",
                        },
                      ];
                      return false;
                    }
                  }
                  var valid1 = _errs3 === errors;
                  if (!valid1) {
                    break;
                  }
                }
              } else {
                validate31.errors = [
                  {
                    instancePath: instancePath + "/alarms",
                    schemaPath: "#/properties/alarms/type",
                    keyword: "type",
                    params: { type: "array" },
                    message: "must be array",
                  },
                ];
                return false;
              }
            }
            var valid0 = _errs1 === errors;
          } else {
            var valid0 = true;
          }
          if (valid0) {
            if (data.available !== void 0) {
              const _errs21 = errors;
              if (typeof data.available !== "boolean") {
                validate31.errors = [
                  {
                    instancePath: instancePath + "/available",
                    schemaPath: "#/properties/available/type",
                    keyword: "type",
                    params: { type: "boolean" },
                    message: "must be boolean",
                  },
                ];
                return false;
              }
              var valid0 = _errs21 === errors;
            } else {
              var valid0 = true;
            }
          }
        } else {
          validate31.errors = [
            {
              instancePath,
              schemaPath: "#/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            },
          ];
          return false;
        }
      }
      validate31.errors = vErrors;
      return errors === 0;
    }
    validate31.evaluated = {
      props: { alarms: true, available: true },
      dynamicProps: false,
      dynamicItems: false,
    };
    var schema49 = {
      additionalProperties: false,
      properties: {
        error: {
          anyOf: [{ maxLength: 64, type: "string" }, { type: "null" }],
          default: null,
          title: "Error",
        },
        errors: { default: 0, minimum: 0, title: "Errors", type: "integer" },
        input_level_rms: {
          default: 0,
          maximum: 1,
          minimum: 0,
          title: "Input Level Rms",
          type: "number",
        },
        metrics: {
          additionalProperties: { type: "number" },
          maxProperties: 16,
          title: "Metrics",
          type: "object",
        },
        microphone: { default: false, title: "Microphone", type: "boolean" },
        muted: { default: true, title: "Muted", type: "boolean" },
        speaker: { default: false, title: "Speaker", type: "boolean" },
        state: {
          enum: [
            "STARTING",
            "IDLE",
            "WAKE_DETECTED",
            "LISTENING",
            "UPLOADING",
            "TRANSCRIBING",
            "THINKING",
            "TOOL_EXECUTING",
            "SYNTHESIZING",
            "DELIVERING",
            "SPEAKING",
            "FOLLOW_UP",
            "ERROR",
          ],
          title: "State",
          type: "string",
        },
        vad_ready: { default: false, title: "Vad Ready", type: "boolean" },
        wake_ready: { default: false, title: "Wake Ready", type: "boolean" },
      },
      required: ["state"],
      title: "EdgeVoicePayload",
      type: "object",
    };
    function validate33(
      data,
      {
        instancePath = "",
        parentData,
        parentDataProperty,
        rootData = data,
        dynamicAnchors = {},
      } = {},
    ) {
      let vErrors = null;
      let errors = 0;
      const evaluated0 = validate33.evaluated;
      if (evaluated0.dynamicProps) {
        evaluated0.props = void 0;
      }
      if (evaluated0.dynamicItems) {
        evaluated0.items = void 0;
      }
      if (errors === 0) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          let missing0;
          if (data.device_id === void 0 && (missing0 = "device_id")) {
            validate33.errors = [
              {
                instancePath,
                schemaPath: "#/required",
                keyword: "required",
                params: { missingProperty: missing0 },
                message: "must have required property '" + missing0 + "'",
              },
            ];
            return false;
          } else {
            const _errs1 = errors;
            for (const key0 in data) {
              if (
                !(
                  key0 === "application" ||
                  key0 === "connected" ||
                  key0 === "device_id" ||
                  key0 === "edge" ||
                  key0 === "last_success"
                )
              ) {
                validate33.errors = [
                  {
                    instancePath,
                    schemaPath: "#/additionalProperties",
                    keyword: "additionalProperties",
                    params: { additionalProperty: key0 },
                    message: "must NOT have additional properties",
                  },
                ];
                return false;
                break;
              }
            }
            if (_errs1 === errors) {
              if (data.application !== void 0) {
                let data0 = data.application;
                const _errs2 = errors;
                const _errs3 = errors;
                let valid1 = false;
                const _errs4 = errors;
                if (
                  !validate23(data0, {
                    instancePath: instancePath + "/application",
                    parentData: data,
                    parentDataProperty: "application",
                    rootData,
                    dynamicAnchors,
                  })
                ) {
                  vErrors =
                    vErrors === null
                      ? validate23.errors
                      : vErrors.concat(validate23.errors);
                  errors = vErrors.length;
                }
                var _valid0 = _errs4 === errors;
                valid1 = valid1 || _valid0;
                const _errs5 = errors;
                if (data0 !== null) {
                  const err0 = {
                    instancePath: instancePath + "/application",
                    schemaPath: "#/properties/application/anyOf/1/type",
                    keyword: "type",
                    params: { type: "null" },
                    message: "must be null",
                  };
                  if (vErrors === null) {
                    vErrors = [err0];
                  } else {
                    vErrors.push(err0);
                  }
                  errors++;
                }
                var _valid0 = _errs5 === errors;
                valid1 = valid1 || _valid0;
                if (!valid1) {
                  const err1 = {
                    instancePath: instancePath + "/application",
                    schemaPath: "#/properties/application/anyOf",
                    keyword: "anyOf",
                    params: {},
                    message: "must match a schema in anyOf",
                  };
                  if (vErrors === null) {
                    vErrors = [err1];
                  } else {
                    vErrors.push(err1);
                  }
                  errors++;
                  validate33.errors = vErrors;
                  return false;
                } else {
                  errors = _errs3;
                  if (vErrors !== null) {
                    if (_errs3) {
                      vErrors.length = _errs3;
                    } else {
                      vErrors = null;
                    }
                  }
                }
                var valid0 = _errs2 === errors;
              } else {
                var valid0 = true;
              }
              if (valid0) {
                if (data.connected !== void 0) {
                  const _errs7 = errors;
                  if (typeof data.connected !== "boolean") {
                    validate33.errors = [
                      {
                        instancePath: instancePath + "/connected",
                        schemaPath: "#/properties/connected/type",
                        keyword: "type",
                        params: { type: "boolean" },
                        message: "must be boolean",
                      },
                    ];
                    return false;
                  }
                  var valid0 = _errs7 === errors;
                } else {
                  var valid0 = true;
                }
                if (valid0) {
                  if (data.device_id !== void 0) {
                    let data2 = data.device_id;
                    const _errs9 = errors;
                    if (errors === _errs9) {
                      if (typeof data2 === "string") {
                        if (func2(data2) > 64) {
                          validate33.errors = [
                            {
                              instancePath: instancePath + "/device_id",
                              schemaPath: "#/properties/device_id/maxLength",
                              keyword: "maxLength",
                              params: { limit: 64 },
                              message: "must NOT have more than 64 characters",
                            },
                          ];
                          return false;
                        } else {
                          if (func2(data2) < 1) {
                            validate33.errors = [
                              {
                                instancePath: instancePath + "/device_id",
                                schemaPath: "#/properties/device_id/minLength",
                                keyword: "minLength",
                                params: { limit: 1 },
                                message:
                                  "must NOT have fewer than 1 characters",
                              },
                            ];
                            return false;
                          } else {
                            if (!pattern4.test(data2)) {
                              validate33.errors = [
                                {
                                  instancePath: instancePath + "/device_id",
                                  schemaPath: "#/properties/device_id/pattern",
                                  keyword: "pattern",
                                  params: { pattern: "^[a-zA-Z0-9_-]+$" },
                                  message:
                                    'must match pattern "^[a-zA-Z0-9_-]+$"',
                                },
                              ];
                              return false;
                            }
                          }
                        }
                      } else {
                        validate33.errors = [
                          {
                            instancePath: instancePath + "/device_id",
                            schemaPath: "#/properties/device_id/type",
                            keyword: "type",
                            params: { type: "string" },
                            message: "must be string",
                          },
                        ];
                        return false;
                      }
                    }
                    var valid0 = _errs9 === errors;
                  } else {
                    var valid0 = true;
                  }
                  if (valid0) {
                    if (data.edge !== void 0) {
                      let data3 = data.edge;
                      const _errs11 = errors;
                      const _errs12 = errors;
                      let valid2 = false;
                      const _errs13 = errors;
                      const _errs14 = errors;
                      if (errors === _errs14) {
                        if (
                          data3 &&
                          typeof data3 == "object" &&
                          !Array.isArray(data3)
                        ) {
                          let missing1;
                          if (data3.state === void 0 && (missing1 = "state")) {
                            const err2 = {
                              instancePath: instancePath + "/edge",
                              schemaPath: "#/$defs/EdgeVoicePayload/required",
                              keyword: "required",
                              params: { missingProperty: missing1 },
                              message:
                                "must have required property '" +
                                missing1 +
                                "'",
                            };
                            if (vErrors === null) {
                              vErrors = [err2];
                            } else {
                              vErrors.push(err2);
                            }
                            errors++;
                          } else {
                            const _errs16 = errors;
                            for (const key1 in data3) {
                              if (!func1.call(schema49.properties, key1)) {
                                const err3 = {
                                  instancePath: instancePath + "/edge",
                                  schemaPath:
                                    "#/$defs/EdgeVoicePayload/additionalProperties",
                                  keyword: "additionalProperties",
                                  params: { additionalProperty: key1 },
                                  message:
                                    "must NOT have additional properties",
                                };
                                if (vErrors === null) {
                                  vErrors = [err3];
                                } else {
                                  vErrors.push(err3);
                                }
                                errors++;
                                break;
                              }
                            }
                            if (_errs16 === errors) {
                              if (data3.error !== void 0) {
                                let data4 = data3.error;
                                const _errs17 = errors;
                                const _errs18 = errors;
                                let valid5 = false;
                                const _errs19 = errors;
                                if (errors === _errs19) {
                                  if (typeof data4 === "string") {
                                    if (func2(data4) > 64) {
                                      const err4 = {
                                        instancePath:
                                          instancePath + "/edge/error",
                                        schemaPath:
                                          "#/$defs/EdgeVoicePayload/properties/error/anyOf/0/maxLength",
                                        keyword: "maxLength",
                                        params: { limit: 64 },
                                        message:
                                          "must NOT have more than 64 characters",
                                      };
                                      if (vErrors === null) {
                                        vErrors = [err4];
                                      } else {
                                        vErrors.push(err4);
                                      }
                                      errors++;
                                    }
                                  } else {
                                    const err5 = {
                                      instancePath:
                                        instancePath + "/edge/error",
                                      schemaPath:
                                        "#/$defs/EdgeVoicePayload/properties/error/anyOf/0/type",
                                      keyword: "type",
                                      params: { type: "string" },
                                      message: "must be string",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err5];
                                    } else {
                                      vErrors.push(err5);
                                    }
                                    errors++;
                                  }
                                }
                                var _valid2 = _errs19 === errors;
                                valid5 = valid5 || _valid2;
                                const _errs21 = errors;
                                if (data4 !== null) {
                                  const err6 = {
                                    instancePath: instancePath + "/edge/error",
                                    schemaPath:
                                      "#/$defs/EdgeVoicePayload/properties/error/anyOf/1/type",
                                    keyword: "type",
                                    params: { type: "null" },
                                    message: "must be null",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err6];
                                  } else {
                                    vErrors.push(err6);
                                  }
                                  errors++;
                                }
                                var _valid2 = _errs21 === errors;
                                valid5 = valid5 || _valid2;
                                if (!valid5) {
                                  const err7 = {
                                    instancePath: instancePath + "/edge/error",
                                    schemaPath:
                                      "#/$defs/EdgeVoicePayload/properties/error/anyOf",
                                    keyword: "anyOf",
                                    params: {},
                                    message: "must match a schema in anyOf",
                                  };
                                  if (vErrors === null) {
                                    vErrors = [err7];
                                  } else {
                                    vErrors.push(err7);
                                  }
                                  errors++;
                                } else {
                                  errors = _errs18;
                                  if (vErrors !== null) {
                                    if (_errs18) {
                                      vErrors.length = _errs18;
                                    } else {
                                      vErrors = null;
                                    }
                                  }
                                }
                                var valid4 = _errs17 === errors;
                              } else {
                                var valid4 = true;
                              }
                              if (valid4) {
                                if (data3.errors !== void 0) {
                                  let data5 = data3.errors;
                                  const _errs23 = errors;
                                  if (
                                    !(
                                      typeof data5 == "number" &&
                                      !(data5 % 1) &&
                                      !isNaN(data5)
                                    )
                                  ) {
                                    const err8 = {
                                      instancePath:
                                        instancePath + "/edge/errors",
                                      schemaPath:
                                        "#/$defs/EdgeVoicePayload/properties/errors/type",
                                      keyword: "type",
                                      params: { type: "integer" },
                                      message: "must be integer",
                                    };
                                    if (vErrors === null) {
                                      vErrors = [err8];
                                    } else {
                                      vErrors.push(err8);
                                    }
                                    errors++;
                                  }
                                  if (errors === _errs23) {
                                    if (typeof data5 == "number") {
                                      if (data5 < 0 || isNaN(data5)) {
                                        const err9 = {
                                          instancePath:
                                            instancePath + "/edge/errors",
                                          schemaPath:
                                            "#/$defs/EdgeVoicePayload/properties/errors/minimum",
                                          keyword: "minimum",
                                          params: {
                                            comparison: ">=",
                                            limit: 0,
                                          },
                                          message: "must be >= 0",
                                        };
                                        if (vErrors === null) {
                                          vErrors = [err9];
                                        } else {
                                          vErrors.push(err9);
                                        }
                                        errors++;
                                      }
                                    }
                                  }
                                  var valid4 = _errs23 === errors;
                                } else {
                                  var valid4 = true;
                                }
                                if (valid4) {
                                  if (data3.input_level_rms !== void 0) {
                                    let data6 = data3.input_level_rms;
                                    const _errs25 = errors;
                                    if (errors === _errs25) {
                                      if (typeof data6 == "number") {
                                        if (data6 > 1 || isNaN(data6)) {
                                          const err10 = {
                                            instancePath:
                                              instancePath +
                                              "/edge/input_level_rms",
                                            schemaPath:
                                              "#/$defs/EdgeVoicePayload/properties/input_level_rms/maximum",
                                            keyword: "maximum",
                                            params: {
                                              comparison: "<=",
                                              limit: 1,
                                            },
                                            message: "must be <= 1",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err10];
                                          } else {
                                            vErrors.push(err10);
                                          }
                                          errors++;
                                        } else {
                                          if (data6 < 0 || isNaN(data6)) {
                                            const err11 = {
                                              instancePath:
                                                instancePath +
                                                "/edge/input_level_rms",
                                              schemaPath:
                                                "#/$defs/EdgeVoicePayload/properties/input_level_rms/minimum",
                                              keyword: "minimum",
                                              params: {
                                                comparison: ">=",
                                                limit: 0,
                                              },
                                              message: "must be >= 0",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err11];
                                            } else {
                                              vErrors.push(err11);
                                            }
                                            errors++;
                                          }
                                        }
                                      } else {
                                        const err12 = {
                                          instancePath:
                                            instancePath +
                                            "/edge/input_level_rms",
                                          schemaPath:
                                            "#/$defs/EdgeVoicePayload/properties/input_level_rms/type",
                                          keyword: "type",
                                          params: { type: "number" },
                                          message: "must be number",
                                        };
                                        if (vErrors === null) {
                                          vErrors = [err12];
                                        } else {
                                          vErrors.push(err12);
                                        }
                                        errors++;
                                      }
                                    }
                                    var valid4 = _errs25 === errors;
                                  } else {
                                    var valid4 = true;
                                  }
                                  if (valid4) {
                                    if (data3.metrics !== void 0) {
                                      let data7 = data3.metrics;
                                      const _errs27 = errors;
                                      if (errors === _errs27) {
                                        if (
                                          data7 &&
                                          typeof data7 == "object" &&
                                          !Array.isArray(data7)
                                        ) {
                                          if (Object.keys(data7).length > 16) {
                                            const err13 = {
                                              instancePath:
                                                instancePath + "/edge/metrics",
                                              schemaPath:
                                                "#/$defs/EdgeVoicePayload/properties/metrics/maxProperties",
                                              keyword: "maxProperties",
                                              params: { limit: 16 },
                                              message:
                                                "must NOT have more than 16 properties",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err13];
                                            } else {
                                              vErrors.push(err13);
                                            }
                                            errors++;
                                          } else {
                                            for (const key2 in data7) {
                                              const _errs30 = errors;
                                              if (
                                                !(
                                                  typeof data7[key2] == "number"
                                                )
                                              ) {
                                                const err14 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/edge/metrics/" +
                                                    key2
                                                      .replace(/~/g, "~0")
                                                      .replace(/\//g, "~1"),
                                                  schemaPath:
                                                    "#/$defs/EdgeVoicePayload/properties/metrics/additionalProperties/type",
                                                  keyword: "type",
                                                  params: { type: "number" },
                                                  message: "must be number",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err14];
                                                } else {
                                                  vErrors.push(err14);
                                                }
                                                errors++;
                                              }
                                              var valid6 = _errs30 === errors;
                                              if (!valid6) {
                                                break;
                                              }
                                            }
                                          }
                                        } else {
                                          const err15 = {
                                            instancePath:
                                              instancePath + "/edge/metrics",
                                            schemaPath:
                                              "#/$defs/EdgeVoicePayload/properties/metrics/type",
                                            keyword: "type",
                                            params: { type: "object" },
                                            message: "must be object",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err15];
                                          } else {
                                            vErrors.push(err15);
                                          }
                                          errors++;
                                        }
                                      }
                                      var valid4 = _errs27 === errors;
                                    } else {
                                      var valid4 = true;
                                    }
                                    if (valid4) {
                                      if (data3.microphone !== void 0) {
                                        const _errs32 = errors;
                                        if (
                                          typeof data3.microphone !== "boolean"
                                        ) {
                                          const err16 = {
                                            instancePath:
                                              instancePath + "/edge/microphone",
                                            schemaPath:
                                              "#/$defs/EdgeVoicePayload/properties/microphone/type",
                                            keyword: "type",
                                            params: { type: "boolean" },
                                            message: "must be boolean",
                                          };
                                          if (vErrors === null) {
                                            vErrors = [err16];
                                          } else {
                                            vErrors.push(err16);
                                          }
                                          errors++;
                                        }
                                        var valid4 = _errs32 === errors;
                                      } else {
                                        var valid4 = true;
                                      }
                                      if (valid4) {
                                        if (data3.muted !== void 0) {
                                          const _errs34 = errors;
                                          if (
                                            typeof data3.muted !== "boolean"
                                          ) {
                                            const err17 = {
                                              instancePath:
                                                instancePath + "/edge/muted",
                                              schemaPath:
                                                "#/$defs/EdgeVoicePayload/properties/muted/type",
                                              keyword: "type",
                                              params: { type: "boolean" },
                                              message: "must be boolean",
                                            };
                                            if (vErrors === null) {
                                              vErrors = [err17];
                                            } else {
                                              vErrors.push(err17);
                                            }
                                            errors++;
                                          }
                                          var valid4 = _errs34 === errors;
                                        } else {
                                          var valid4 = true;
                                        }
                                        if (valid4) {
                                          if (data3.speaker !== void 0) {
                                            const _errs36 = errors;
                                            if (
                                              typeof data3.speaker !== "boolean"
                                            ) {
                                              const err18 = {
                                                instancePath:
                                                  instancePath +
                                                  "/edge/speaker",
                                                schemaPath:
                                                  "#/$defs/EdgeVoicePayload/properties/speaker/type",
                                                keyword: "type",
                                                params: { type: "boolean" },
                                                message: "must be boolean",
                                              };
                                              if (vErrors === null) {
                                                vErrors = [err18];
                                              } else {
                                                vErrors.push(err18);
                                              }
                                              errors++;
                                            }
                                            var valid4 = _errs36 === errors;
                                          } else {
                                            var valid4 = true;
                                          }
                                          if (valid4) {
                                            if (data3.state !== void 0) {
                                              let data12 = data3.state;
                                              const _errs38 = errors;
                                              if (typeof data12 !== "string") {
                                                const err19 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/edge/state",
                                                  schemaPath:
                                                    "#/$defs/EdgeVoicePayload/properties/state/type",
                                                  keyword: "type",
                                                  params: { type: "string" },
                                                  message: "must be string",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err19];
                                                } else {
                                                  vErrors.push(err19);
                                                }
                                                errors++;
                                              }
                                              if (
                                                !(
                                                  data12 === "STARTING" ||
                                                  data12 === "IDLE" ||
                                                  data12 === "WAKE_DETECTED" ||
                                                  data12 === "LISTENING" ||
                                                  data12 === "UPLOADING" ||
                                                  data12 === "TRANSCRIBING" ||
                                                  data12 === "THINKING" ||
                                                  data12 === "TOOL_EXECUTING" ||
                                                  data12 === "SYNTHESIZING" ||
                                                  data12 === "DELIVERING" ||
                                                  data12 === "SPEAKING" ||
                                                  data12 === "FOLLOW_UP" ||
                                                  data12 === "ERROR"
                                                )
                                              ) {
                                                const err20 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/edge/state",
                                                  schemaPath:
                                                    "#/$defs/EdgeVoicePayload/properties/state/enum",
                                                  keyword: "enum",
                                                  params: {
                                                    allowedValues:
                                                      schema49.properties.state
                                                        .enum,
                                                  },
                                                  message:
                                                    "must be equal to one of the allowed values",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err20];
                                                } else {
                                                  vErrors.push(err20);
                                                }
                                                errors++;
                                              }
                                              var valid4 = _errs38 === errors;
                                            } else {
                                              var valid4 = true;
                                            }
                                            if (valid4) {
                                              if (data3.vad_ready !== void 0) {
                                                const _errs40 = errors;
                                                if (
                                                  typeof data3.vad_ready !==
                                                  "boolean"
                                                ) {
                                                  const err21 = {
                                                    instancePath:
                                                      instancePath +
                                                      "/edge/vad_ready",
                                                    schemaPath:
                                                      "#/$defs/EdgeVoicePayload/properties/vad_ready/type",
                                                    keyword: "type",
                                                    params: { type: "boolean" },
                                                    message: "must be boolean",
                                                  };
                                                  if (vErrors === null) {
                                                    vErrors = [err21];
                                                  } else {
                                                    vErrors.push(err21);
                                                  }
                                                  errors++;
                                                }
                                                var valid4 = _errs40 === errors;
                                              } else {
                                                var valid4 = true;
                                              }
                                              if (valid4) {
                                                if (
                                                  data3.wake_ready !== void 0
                                                ) {
                                                  const _errs42 = errors;
                                                  if (
                                                    typeof data3.wake_ready !==
                                                    "boolean"
                                                  ) {
                                                    const err22 = {
                                                      instancePath:
                                                        instancePath +
                                                        "/edge/wake_ready",
                                                      schemaPath:
                                                        "#/$defs/EdgeVoicePayload/properties/wake_ready/type",
                                                      keyword: "type",
                                                      params: {
                                                        type: "boolean",
                                                      },
                                                      message:
                                                        "must be boolean",
                                                    };
                                                    if (vErrors === null) {
                                                      vErrors = [err22];
                                                    } else {
                                                      vErrors.push(err22);
                                                    }
                                                    errors++;
                                                  }
                                                  var valid4 =
                                                    _errs42 === errors;
                                                } else {
                                                  var valid4 = true;
                                                }
                                              }
                                            }
                                          }
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                            }
                          }
                        } else {
                          const err23 = {
                            instancePath: instancePath + "/edge",
                            schemaPath: "#/$defs/EdgeVoicePayload/type",
                            keyword: "type",
                            params: { type: "object" },
                            message: "must be object",
                          };
                          if (vErrors === null) {
                            vErrors = [err23];
                          } else {
                            vErrors.push(err23);
                          }
                          errors++;
                        }
                      }
                      var _valid1 = _errs13 === errors;
                      valid2 = valid2 || _valid1;
                      const _errs44 = errors;
                      if (data3 !== null) {
                        const err24 = {
                          instancePath: instancePath + "/edge",
                          schemaPath: "#/properties/edge/anyOf/1/type",
                          keyword: "type",
                          params: { type: "null" },
                          message: "must be null",
                        };
                        if (vErrors === null) {
                          vErrors = [err24];
                        } else {
                          vErrors.push(err24);
                        }
                        errors++;
                      }
                      var _valid1 = _errs44 === errors;
                      valid2 = valid2 || _valid1;
                      if (!valid2) {
                        const err25 = {
                          instancePath: instancePath + "/edge",
                          schemaPath: "#/properties/edge/anyOf",
                          keyword: "anyOf",
                          params: {},
                          message: "must match a schema in anyOf",
                        };
                        if (vErrors === null) {
                          vErrors = [err25];
                        } else {
                          vErrors.push(err25);
                        }
                        errors++;
                        validate33.errors = vErrors;
                        return false;
                      } else {
                        errors = _errs12;
                        if (vErrors !== null) {
                          if (_errs12) {
                            vErrors.length = _errs12;
                          } else {
                            vErrors = null;
                          }
                        }
                      }
                      var valid0 = _errs11 === errors;
                    } else {
                      var valid0 = true;
                    }
                    if (valid0) {
                      if (data.last_success !== void 0) {
                        let data15 = data.last_success;
                        const _errs46 = errors;
                        const _errs47 = errors;
                        let valid7 = false;
                        const _errs48 = errors;
                        if (errors === _errs48) {
                          if (errors === _errs48) {
                            if (typeof data15 === "string") {
                              if (!formats2.validate(data15)) {
                                const err26 = {
                                  instancePath: instancePath + "/last_success",
                                  schemaPath:
                                    "#/properties/last_success/anyOf/0/format",
                                  keyword: "format",
                                  params: { format: "date-time" },
                                  message: 'must match format "date-time"',
                                };
                                if (vErrors === null) {
                                  vErrors = [err26];
                                } else {
                                  vErrors.push(err26);
                                }
                                errors++;
                              }
                            } else {
                              const err27 = {
                                instancePath: instancePath + "/last_success",
                                schemaPath:
                                  "#/properties/last_success/anyOf/0/type",
                                keyword: "type",
                                params: { type: "string" },
                                message: "must be string",
                              };
                              if (vErrors === null) {
                                vErrors = [err27];
                              } else {
                                vErrors.push(err27);
                              }
                              errors++;
                            }
                          }
                        }
                        var _valid3 = _errs48 === errors;
                        valid7 = valid7 || _valid3;
                        const _errs50 = errors;
                        if (data15 !== null) {
                          const err28 = {
                            instancePath: instancePath + "/last_success",
                            schemaPath:
                              "#/properties/last_success/anyOf/1/type",
                            keyword: "type",
                            params: { type: "null" },
                            message: "must be null",
                          };
                          if (vErrors === null) {
                            vErrors = [err28];
                          } else {
                            vErrors.push(err28);
                          }
                          errors++;
                        }
                        var _valid3 = _errs50 === errors;
                        valid7 = valid7 || _valid3;
                        if (!valid7) {
                          const err29 = {
                            instancePath: instancePath + "/last_success",
                            schemaPath: "#/properties/last_success/anyOf",
                            keyword: "anyOf",
                            params: {},
                            message: "must match a schema in anyOf",
                          };
                          if (vErrors === null) {
                            vErrors = [err29];
                          } else {
                            vErrors.push(err29);
                          }
                          errors++;
                          validate33.errors = vErrors;
                          return false;
                        } else {
                          errors = _errs47;
                          if (vErrors !== null) {
                            if (_errs47) {
                              vErrors.length = _errs47;
                            } else {
                              vErrors = null;
                            }
                          }
                        }
                        var valid0 = _errs46 === errors;
                      } else {
                        var valid0 = true;
                      }
                    }
                  }
                }
              }
            }
          }
        } else {
          validate33.errors = [
            {
              instancePath,
              schemaPath: "#/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            },
          ];
          return false;
        }
      }
      validate33.errors = vErrors;
      return errors === 0;
    }
    validate33.evaluated = {
      props: true,
      dynamicProps: false,
      dynamicItems: false,
    };
    function validate30(
      data,
      {
        instancePath = "",
        parentData,
        parentDataProperty,
        rootData = data,
        dynamicAnchors = {},
      } = {},
    ) {
      let vErrors = null;
      let errors = 0;
      const evaluated0 = validate30.evaluated;
      if (evaluated0.dynamicProps) {
        evaluated0.props = void 0;
      }
      if (evaluated0.dynamicItems) {
        evaluated0.items = void 0;
      }
      if (errors === 0) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          let missing0;
          if (
            (data.revision === void 0 && (missing0 = "revision")) ||
            (data.expires_after_seconds === void 0 &&
              (missing0 = "expires_after_seconds")) ||
            (data.events === void 0 && (missing0 = "events")) ||
            (data.devices === void 0 && (missing0 = "devices"))
          ) {
            validate30.errors = [
              {
                instancePath,
                schemaPath: "#/required",
                keyword: "required",
                params: { missingProperty: missing0 },
                message: "must have required property '" + missing0 + "'",
              },
            ];
            return false;
          } else {
            const _errs1 = errors;
            for (const key0 in data) {
              if (
                !(
                  key0 === "alarm_delivery" ||
                  key0 === "devices" ||
                  key0 === "events" ||
                  key0 === "expires_after_seconds" ||
                  key0 === "resync_required" ||
                  key0 === "revision" ||
                  key0 === "version" ||
                  key0 === "volatile"
                )
              ) {
                validate30.errors = [
                  {
                    instancePath,
                    schemaPath: "#/additionalProperties",
                    keyword: "additionalProperties",
                    params: { additionalProperty: key0 },
                    message: "must NOT have additional properties",
                  },
                ];
                return false;
                break;
              }
            }
            if (_errs1 === errors) {
              if (data.alarm_delivery !== void 0) {
                const _errs2 = errors;
                if (
                  !validate31(data.alarm_delivery, {
                    instancePath: instancePath + "/alarm_delivery",
                    parentData: data,
                    parentDataProperty: "alarm_delivery",
                    rootData,
                    dynamicAnchors,
                  })
                ) {
                  vErrors =
                    vErrors === null
                      ? validate31.errors
                      : vErrors.concat(validate31.errors);
                  errors = vErrors.length;
                }
                var valid0 = _errs2 === errors;
              } else {
                var valid0 = true;
              }
              if (valid0) {
                if (data.devices !== void 0) {
                  let data1 = data.devices;
                  const _errs3 = errors;
                  if (errors === _errs3) {
                    if (Array.isArray(data1)) {
                      var valid1 = true;
                      const len0 = data1.length;
                      for (let i0 = 0; i0 < len0; i0++) {
                        const _errs5 = errors;
                        if (
                          !validate33(data1[i0], {
                            instancePath: instancePath + "/devices/" + i0,
                            parentData: data1,
                            parentDataProperty: i0,
                            rootData,
                            dynamicAnchors,
                          })
                        ) {
                          vErrors =
                            vErrors === null
                              ? validate33.errors
                              : vErrors.concat(validate33.errors);
                          errors = vErrors.length;
                        }
                        var valid1 = _errs5 === errors;
                        if (!valid1) {
                          break;
                        }
                      }
                    } else {
                      validate30.errors = [
                        {
                          instancePath: instancePath + "/devices",
                          schemaPath: "#/properties/devices/type",
                          keyword: "type",
                          params: { type: "array" },
                          message: "must be array",
                        },
                      ];
                      return false;
                    }
                  }
                  var valid0 = _errs3 === errors;
                } else {
                  var valid0 = true;
                }
                if (valid0) {
                  if (data.events !== void 0) {
                    let data3 = data.events;
                    const _errs6 = errors;
                    if (errors === _errs6) {
                      if (Array.isArray(data3)) {
                        var valid2 = true;
                        const len1 = data3.length;
                        for (let i1 = 0; i1 < len1; i1++) {
                          let data4 = data3[i1];
                          const _errs8 = errors;
                          const _errs9 = errors;
                          if (errors === _errs9) {
                            if (
                              data4 &&
                              typeof data4 == "object" &&
                              !Array.isArray(data4)
                            ) {
                              let missing1;
                              if (
                                (data4.version === void 0 &&
                                  (missing1 = "version")) ||
                                (data4.event_id === void 0 &&
                                  (missing1 = "event_id")) ||
                                (data4.revision === void 0 &&
                                  (missing1 = "revision")) ||
                                (data4.timestamp === void 0 &&
                                  (missing1 = "timestamp")) ||
                                (data4.device_id === void 0 &&
                                  (missing1 = "device_id")) ||
                                (data4.type === void 0 &&
                                  (missing1 = "type")) ||
                                (data4.payload === void 0 &&
                                  (missing1 = "payload"))
                              ) {
                                validate30.errors = [
                                  {
                                    instancePath:
                                      instancePath + "/events/" + i1,
                                    schemaPath: "#/$defs/VoiceEvent/required",
                                    keyword: "required",
                                    params: { missingProperty: missing1 },
                                    message:
                                      "must have required property '" +
                                      missing1 +
                                      "'",
                                  },
                                ];
                                return false;
                              } else {
                                const _errs11 = errors;
                                for (const key1 in data4) {
                                  if (
                                    !(
                                      key1 === "device_id" ||
                                      key1 === "event_id" ||
                                      key1 === "payload" ||
                                      key1 === "revision" ||
                                      key1 === "timestamp" ||
                                      key1 === "type" ||
                                      key1 === "version"
                                    )
                                  ) {
                                    validate30.errors = [
                                      {
                                        instancePath:
                                          instancePath + "/events/" + i1,
                                        schemaPath:
                                          "#/$defs/VoiceEvent/additionalProperties",
                                        keyword: "additionalProperties",
                                        params: { additionalProperty: key1 },
                                        message:
                                          "must NOT have additional properties",
                                      },
                                    ];
                                    return false;
                                    break;
                                  }
                                }
                                if (_errs11 === errors) {
                                  if (data4.device_id !== void 0) {
                                    let data5 = data4.device_id;
                                    const _errs12 = errors;
                                    if (errors === _errs12) {
                                      if (typeof data5 === "string") {
                                        if (func2(data5) > 64) {
                                          validate30.errors = [
                                            {
                                              instancePath:
                                                instancePath +
                                                "/events/" +
                                                i1 +
                                                "/device_id",
                                              schemaPath:
                                                "#/$defs/VoiceEvent/properties/device_id/maxLength",
                                              keyword: "maxLength",
                                              params: { limit: 64 },
                                              message:
                                                "must NOT have more than 64 characters",
                                            },
                                          ];
                                          return false;
                                        } else {
                                          if (func2(data5) < 1) {
                                            validate30.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/events/" +
                                                  i1 +
                                                  "/device_id",
                                                schemaPath:
                                                  "#/$defs/VoiceEvent/properties/device_id/minLength",
                                                keyword: "minLength",
                                                params: { limit: 1 },
                                                message:
                                                  "must NOT have fewer than 1 characters",
                                              },
                                            ];
                                            return false;
                                          } else {
                                            if (!pattern4.test(data5)) {
                                              validate30.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/events/" +
                                                    i1 +
                                                    "/device_id",
                                                  schemaPath:
                                                    "#/$defs/VoiceEvent/properties/device_id/pattern",
                                                  keyword: "pattern",
                                                  params: {
                                                    pattern: "^[a-zA-Z0-9_-]+$",
                                                  },
                                                  message:
                                                    'must match pattern "^[a-zA-Z0-9_-]+$"',
                                                },
                                              ];
                                              return false;
                                            }
                                          }
                                        }
                                      } else {
                                        validate30.errors = [
                                          {
                                            instancePath:
                                              instancePath +
                                              "/events/" +
                                              i1 +
                                              "/device_id",
                                            schemaPath:
                                              "#/$defs/VoiceEvent/properties/device_id/type",
                                            keyword: "type",
                                            params: { type: "string" },
                                            message: "must be string",
                                          },
                                        ];
                                        return false;
                                      }
                                    }
                                    var valid4 = _errs12 === errors;
                                  } else {
                                    var valid4 = true;
                                  }
                                  if (valid4) {
                                    if (data4.event_id !== void 0) {
                                      let data6 = data4.event_id;
                                      const _errs14 = errors;
                                      if (errors === _errs14) {
                                        if (errors === _errs14) {
                                          if (typeof data6 === "string") {
                                            if (!formats0.test(data6)) {
                                              validate30.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/events/" +
                                                    i1 +
                                                    "/event_id",
                                                  schemaPath:
                                                    "#/$defs/VoiceEvent/properties/event_id/format",
                                                  keyword: "format",
                                                  params: { format: "uuid" },
                                                  message:
                                                    'must match format "uuid"',
                                                },
                                              ];
                                              return false;
                                            }
                                          } else {
                                            validate30.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/events/" +
                                                  i1 +
                                                  "/event_id",
                                                schemaPath:
                                                  "#/$defs/VoiceEvent/properties/event_id/type",
                                                keyword: "type",
                                                params: { type: "string" },
                                                message: "must be string",
                                              },
                                            ];
                                            return false;
                                          }
                                        }
                                      }
                                      var valid4 = _errs14 === errors;
                                    } else {
                                      var valid4 = true;
                                    }
                                    if (valid4) {
                                      if (data4.payload !== void 0) {
                                        let data7 = data4.payload;
                                        const _errs16 = errors;
                                        if (errors === _errs16) {
                                          if (
                                            data7 &&
                                            typeof data7 == "object" &&
                                            !Array.isArray(data7)
                                          ) {
                                          } else {
                                            validate30.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/events/" +
                                                  i1 +
                                                  "/payload",
                                                schemaPath:
                                                  "#/$defs/VoiceEvent/properties/payload/type",
                                                keyword: "type",
                                                params: { type: "object" },
                                                message: "must be object",
                                              },
                                            ];
                                            return false;
                                          }
                                        }
                                        var valid4 = _errs16 === errors;
                                      } else {
                                        var valid4 = true;
                                      }
                                      if (valid4) {
                                        if (data4.revision !== void 0) {
                                          let data8 = data4.revision;
                                          const _errs19 = errors;
                                          if (
                                            !(
                                              typeof data8 == "number" &&
                                              !(data8 % 1) &&
                                              !isNaN(data8)
                                            )
                                          ) {
                                            validate30.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/events/" +
                                                  i1 +
                                                  "/revision",
                                                schemaPath:
                                                  "#/$defs/VoiceEvent/properties/revision/type",
                                                keyword: "type",
                                                params: { type: "integer" },
                                                message: "must be integer",
                                              },
                                            ];
                                            return false;
                                          }
                                          if (errors === _errs19) {
                                            if (typeof data8 == "number") {
                                              if (data8 < 1 || isNaN(data8)) {
                                                validate30.errors = [
                                                  {
                                                    instancePath:
                                                      instancePath +
                                                      "/events/" +
                                                      i1 +
                                                      "/revision",
                                                    schemaPath:
                                                      "#/$defs/VoiceEvent/properties/revision/minimum",
                                                    keyword: "minimum",
                                                    params: {
                                                      comparison: ">=",
                                                      limit: 1,
                                                    },
                                                    message: "must be >= 1",
                                                  },
                                                ];
                                                return false;
                                              }
                                            }
                                          }
                                          var valid4 = _errs19 === errors;
                                        } else {
                                          var valid4 = true;
                                        }
                                        if (valid4) {
                                          if (data4.timestamp !== void 0) {
                                            let data9 = data4.timestamp;
                                            const _errs21 = errors;
                                            if (errors === _errs21) {
                                              if (errors === _errs21) {
                                                if (typeof data9 === "string") {
                                                  if (
                                                    !formats2.validate(data9)
                                                  ) {
                                                    validate30.errors = [
                                                      {
                                                        instancePath:
                                                          instancePath +
                                                          "/events/" +
                                                          i1 +
                                                          "/timestamp",
                                                        schemaPath:
                                                          "#/$defs/VoiceEvent/properties/timestamp/format",
                                                        keyword: "format",
                                                        params: {
                                                          format: "date-time",
                                                        },
                                                        message:
                                                          'must match format "date-time"',
                                                      },
                                                    ];
                                                    return false;
                                                  }
                                                } else {
                                                  validate30.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/events/" +
                                                        i1 +
                                                        "/timestamp",
                                                      schemaPath:
                                                        "#/$defs/VoiceEvent/properties/timestamp/type",
                                                      keyword: "type",
                                                      params: {
                                                        type: "string",
                                                      },
                                                      message: "must be string",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                              }
                                            }
                                            var valid4 = _errs21 === errors;
                                          } else {
                                            var valid4 = true;
                                          }
                                          if (valid4) {
                                            if (data4.type !== void 0) {
                                              let data10 = data4.type;
                                              const _errs23 = errors;
                                              if (typeof data10 !== "string") {
                                                validate30.errors = [
                                                  {
                                                    instancePath:
                                                      instancePath +
                                                      "/events/" +
                                                      i1 +
                                                      "/type",
                                                    schemaPath:
                                                      "#/$defs/VoiceEvent/properties/type/type",
                                                    keyword: "type",
                                                    params: { type: "string" },
                                                    message: "must be string",
                                                  },
                                                ];
                                                return false;
                                              }
                                              if (
                                                !(
                                                  data10 ===
                                                    "assistant.transcribing" ||
                                                  data10 ===
                                                    "assistant.thinking" ||
                                                  data10 ===
                                                    "assistant.tool_executing" ||
                                                  data10 ===
                                                    "assistant.synthesizing" ||
                                                  data10 ===
                                                    "assistant.delivering" ||
                                                  data10 ===
                                                    "assistant.speaking" ||
                                                  data10 ===
                                                    "assistant.follow_up" ||
                                                  data10 ===
                                                    "assistant.error" ||
                                                  data10 ===
                                                    "assistant.edge_state" ||
                                                  data10 ===
                                                    "assistant.playback"
                                                )
                                              ) {
                                                validate30.errors = [
                                                  {
                                                    instancePath:
                                                      instancePath +
                                                      "/events/" +
                                                      i1 +
                                                      "/type",
                                                    schemaPath:
                                                      "#/$defs/VoiceEvent/properties/type/enum",
                                                    keyword: "enum",
                                                    params: {
                                                      allowedValues:
                                                        schema50.properties.type
                                                          .enum,
                                                    },
                                                    message:
                                                      "must be equal to one of the allowed values",
                                                  },
                                                ];
                                                return false;
                                              }
                                              var valid4 = _errs23 === errors;
                                            } else {
                                              var valid4 = true;
                                            }
                                            if (valid4) {
                                              if (data4.version !== void 0) {
                                                let data11 = data4.version;
                                                const _errs25 = errors;
                                                if (
                                                  !(
                                                    typeof data11 == "number" &&
                                                    !(data11 % 1) &&
                                                    !isNaN(data11)
                                                  )
                                                ) {
                                                  validate30.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/events/" +
                                                        i1 +
                                                        "/version",
                                                      schemaPath:
                                                        "#/$defs/VoiceEvent/properties/version/type",
                                                      keyword: "type",
                                                      params: {
                                                        type: "integer",
                                                      },
                                                      message:
                                                        "must be integer",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                                if (1 !== data11) {
                                                  validate30.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/events/" +
                                                        i1 +
                                                        "/version",
                                                      schemaPath:
                                                        "#/$defs/VoiceEvent/properties/version/const",
                                                      keyword: "const",
                                                      params: {
                                                        allowedValue: 1,
                                                      },
                                                      message:
                                                        "must be equal to constant",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                                var valid4 = _errs25 === errors;
                                              } else {
                                                var valid4 = true;
                                              }
                                            }
                                          }
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                            } else {
                              validate30.errors = [
                                {
                                  instancePath: instancePath + "/events/" + i1,
                                  schemaPath: "#/$defs/VoiceEvent/type",
                                  keyword: "type",
                                  params: { type: "object" },
                                  message: "must be object",
                                },
                              ];
                              return false;
                            }
                          }
                          var valid2 = _errs8 === errors;
                          if (!valid2) {
                            break;
                          }
                        }
                      } else {
                        validate30.errors = [
                          {
                            instancePath: instancePath + "/events",
                            schemaPath: "#/properties/events/type",
                            keyword: "type",
                            params: { type: "array" },
                            message: "must be array",
                          },
                        ];
                        return false;
                      }
                    }
                    var valid0 = _errs6 === errors;
                  } else {
                    var valid0 = true;
                  }
                  if (valid0) {
                    if (data.expires_after_seconds !== void 0) {
                      let data12 = data.expires_after_seconds;
                      const _errs27 = errors;
                      if (errors === _errs27) {
                        if (typeof data12 == "number") {
                          if (data12 <= 0 || isNaN(data12)) {
                            validate30.errors = [
                              {
                                instancePath:
                                  instancePath + "/expires_after_seconds",
                                schemaPath:
                                  "#/properties/expires_after_seconds/exclusiveMinimum",
                                keyword: "exclusiveMinimum",
                                params: { comparison: ">", limit: 0 },
                                message: "must be > 0",
                              },
                            ];
                            return false;
                          }
                        } else {
                          validate30.errors = [
                            {
                              instancePath:
                                instancePath + "/expires_after_seconds",
                              schemaPath:
                                "#/properties/expires_after_seconds/type",
                              keyword: "type",
                              params: { type: "number" },
                              message: "must be number",
                            },
                          ];
                          return false;
                        }
                      }
                      var valid0 = _errs27 === errors;
                    } else {
                      var valid0 = true;
                    }
                    if (valid0) {
                      if (data.resync_required !== void 0) {
                        const _errs29 = errors;
                        if (typeof data.resync_required !== "boolean") {
                          validate30.errors = [
                            {
                              instancePath: instancePath + "/resync_required",
                              schemaPath: "#/properties/resync_required/type",
                              keyword: "type",
                              params: { type: "boolean" },
                              message: "must be boolean",
                            },
                          ];
                          return false;
                        }
                        var valid0 = _errs29 === errors;
                      } else {
                        var valid0 = true;
                      }
                      if (valid0) {
                        if (data.revision !== void 0) {
                          let data14 = data.revision;
                          const _errs31 = errors;
                          if (
                            !(
                              typeof data14 == "number" &&
                              !(data14 % 1) &&
                              !isNaN(data14)
                            )
                          ) {
                            validate30.errors = [
                              {
                                instancePath: instancePath + "/revision",
                                schemaPath: "#/properties/revision/type",
                                keyword: "type",
                                params: { type: "integer" },
                                message: "must be integer",
                              },
                            ];
                            return false;
                          }
                          if (errors === _errs31) {
                            if (typeof data14 == "number") {
                              if (data14 < 0 || isNaN(data14)) {
                                validate30.errors = [
                                  {
                                    instancePath: instancePath + "/revision",
                                    schemaPath: "#/properties/revision/minimum",
                                    keyword: "minimum",
                                    params: { comparison: ">=", limit: 0 },
                                    message: "must be >= 0",
                                  },
                                ];
                                return false;
                              }
                            }
                          }
                          var valid0 = _errs31 === errors;
                        } else {
                          var valid0 = true;
                        }
                        if (valid0) {
                          if (data.version !== void 0) {
                            let data15 = data.version;
                            const _errs33 = errors;
                            if (
                              !(
                                typeof data15 == "number" &&
                                !(data15 % 1) &&
                                !isNaN(data15)
                              )
                            ) {
                              validate30.errors = [
                                {
                                  instancePath: instancePath + "/version",
                                  schemaPath: "#/properties/version/type",
                                  keyword: "type",
                                  params: { type: "integer" },
                                  message: "must be integer",
                                },
                              ];
                              return false;
                            }
                            if (1 !== data15) {
                              validate30.errors = [
                                {
                                  instancePath: instancePath + "/version",
                                  schemaPath: "#/properties/version/const",
                                  keyword: "const",
                                  params: { allowedValue: 1 },
                                  message: "must be equal to constant",
                                },
                              ];
                              return false;
                            }
                            var valid0 = _errs33 === errors;
                          } else {
                            var valid0 = true;
                          }
                          if (valid0) {
                            if (data.volatile !== void 0) {
                              let data16 = data.volatile;
                              const _errs35 = errors;
                              if (typeof data16 !== "boolean") {
                                validate30.errors = [
                                  {
                                    instancePath: instancePath + "/volatile",
                                    schemaPath: "#/properties/volatile/type",
                                    keyword: "type",
                                    params: { type: "boolean" },
                                    message: "must be boolean",
                                  },
                                ];
                                return false;
                              }
                              if (true !== data16) {
                                validate30.errors = [
                                  {
                                    instancePath: instancePath + "/volatile",
                                    schemaPath: "#/properties/volatile/const",
                                    keyword: "const",
                                    params: { allowedValue: true },
                                    message: "must be equal to constant",
                                  },
                                ];
                                return false;
                              }
                              var valid0 = _errs35 === errors;
                            } else {
                              var valid0 = true;
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        } else {
          validate30.errors = [
            {
              instancePath,
              schemaPath: "#/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            },
          ];
          return false;
        }
      }
      validate30.errors = vErrors;
      return errors === 0;
    }
    validate30.evaluated = {
      props: true,
      dynamicProps: false,
      dynamicItems: false,
    };
    function validate20(
      data,
      {
        instancePath = "",
        parentData,
        parentDataProperty,
        rootData = data,
        dynamicAnchors = {},
      } = {},
    ) {
      let vErrors = null;
      let errors = 0;
      const evaluated0 = validate20.evaluated;
      if (evaluated0.dynamicProps) {
        evaluated0.props = void 0;
      }
      if (evaluated0.dynamicItems) {
        evaluated0.items = void 0;
      }
      if (errors === 0) {
        if (data && typeof data == "object" && !Array.isArray(data)) {
          let missing0;
          if (
            (data.epoch === void 0 && (missing0 = "epoch")) ||
            (data.reset === void 0 && (missing0 = "reset")) ||
            (data.server_time === void 0 && (missing0 = "server_time")) ||
            (data.session === void 0 && (missing0 = "session")) ||
            (data.application === void 0 && (missing0 = "application")) ||
            (data.events === void 0 && (missing0 = "events")) ||
            (data.voice === void 0 && (missing0 = "voice")) ||
            (data.home === void 0 && (missing0 = "home")) ||
            (data.provider === void 0 && (missing0 = "provider")) ||
            (data.model === void 0 && (missing0 = "model"))
          ) {
            validate20.errors = [
              {
                instancePath,
                schemaPath: "#/required",
                keyword: "required",
                params: { missingProperty: missing0 },
                message: "must have required property '" + missing0 + "'",
              },
            ];
            return false;
          } else {
            const _errs1 = errors;
            for (const key0 in data) {
              if (!func1.call(schema31.properties, key0)) {
                validate20.errors = [
                  {
                    instancePath,
                    schemaPath: "#/additionalProperties",
                    keyword: "additionalProperties",
                    params: { additionalProperty: key0 },
                    message: "must NOT have additional properties",
                  },
                ];
                return false;
                break;
              }
            }
            if (_errs1 === errors) {
              if (data.ambient_weather !== void 0) {
                let data0 = data.ambient_weather;
                const _errs2 = errors;
                const _errs3 = errors;
                let valid1 = false;
                const _errs4 = errors;
                if (
                  !validate21(data0, {
                    instancePath: instancePath + "/ambient_weather",
                    parentData: data,
                    parentDataProperty: "ambient_weather",
                    rootData,
                    dynamicAnchors,
                  })
                ) {
                  vErrors =
                    vErrors === null
                      ? validate21.errors
                      : vErrors.concat(validate21.errors);
                  errors = vErrors.length;
                }
                var _valid0 = _errs4 === errors;
                valid1 = valid1 || _valid0;
                if (_valid0) {
                  var props0 = {};
                  props0.cache_age_seconds = true;
                  props0.current = true;
                  props0.daily = true;
                  props0.fetched_at = true;
                  props0.freshness_ttl_seconds = true;
                  props0.hourly = true;
                  props0.location = true;
                  props0.measurement_units = true;
                  props0.source = true;
                  props0.source_age_seconds = true;
                  props0.source_timestamp = true;
                  props0.stale = true;
                  props0.units = true;
                  props0.valid_from = true;
                  props0.valid_until = true;
                  props0.version = true;
                }
                const _errs5 = errors;
                if (data0 !== null) {
                  const err0 = {
                    instancePath: instancePath + "/ambient_weather",
                    schemaPath: "#/properties/ambient_weather/anyOf/1/type",
                    keyword: "type",
                    params: { type: "null" },
                    message: "must be null",
                  };
                  if (vErrors === null) {
                    vErrors = [err0];
                  } else {
                    vErrors.push(err0);
                  }
                  errors++;
                }
                var _valid0 = _errs5 === errors;
                valid1 = valid1 || _valid0;
                if (!valid1) {
                  const err1 = {
                    instancePath: instancePath + "/ambient_weather",
                    schemaPath: "#/properties/ambient_weather/anyOf",
                    keyword: "anyOf",
                    params: {},
                    message: "must match a schema in anyOf",
                  };
                  if (vErrors === null) {
                    vErrors = [err1];
                  } else {
                    vErrors.push(err1);
                  }
                  errors++;
                  validate20.errors = vErrors;
                  return false;
                } else {
                  errors = _errs3;
                  if (vErrors !== null) {
                    if (_errs3) {
                      vErrors.length = _errs3;
                    } else {
                      vErrors = null;
                    }
                  }
                }
                var valid0 = _errs2 === errors;
              } else {
                var valid0 = true;
              }
              if (valid0) {
                if (data.application !== void 0) {
                  const _errs7 = errors;
                  if (
                    !validate23(data.application, {
                      instancePath: instancePath + "/application",
                      parentData: data,
                      parentDataProperty: "application",
                      rootData,
                      dynamicAnchors,
                    })
                  ) {
                    vErrors =
                      vErrors === null
                        ? validate23.errors
                        : vErrors.concat(validate23.errors);
                    errors = vErrors.length;
                  }
                  var valid0 = _errs7 === errors;
                } else {
                  var valid0 = true;
                }
                if (valid0) {
                  if (data.epoch !== void 0) {
                    let data2 = data.epoch;
                    const _errs8 = errors;
                    if (errors === _errs8) {
                      if (errors === _errs8) {
                        if (typeof data2 === "string") {
                          if (!formats0.test(data2)) {
                            validate20.errors = [
                              {
                                instancePath: instancePath + "/epoch",
                                schemaPath: "#/properties/epoch/format",
                                keyword: "format",
                                params: { format: "uuid" },
                                message: 'must match format "uuid"',
                              },
                            ];
                            return false;
                          }
                        } else {
                          validate20.errors = [
                            {
                              instancePath: instancePath + "/epoch",
                              schemaPath: "#/properties/epoch/type",
                              keyword: "type",
                              params: { type: "string" },
                              message: "must be string",
                            },
                          ];
                          return false;
                        }
                      }
                    }
                    var valid0 = _errs8 === errors;
                  } else {
                    var valid0 = true;
                  }
                  if (valid0) {
                    if (data.events !== void 0) {
                      const _errs10 = errors;
                      if (
                        !validate26(data.events, {
                          instancePath: instancePath + "/events",
                          parentData: data,
                          parentDataProperty: "events",
                          rootData,
                          dynamicAnchors,
                        })
                      ) {
                        vErrors =
                          vErrors === null
                            ? validate26.errors
                            : vErrors.concat(validate26.errors);
                        errors = vErrors.length;
                      }
                      var valid0 = _errs10 === errors;
                    } else {
                      var valid0 = true;
                    }
                    if (valid0) {
                      if (data.home !== void 0) {
                        let data4 = data.home;
                        const _errs11 = errors;
                        if (errors === _errs11) {
                          if (Array.isArray(data4)) {
                            var valid2 = true;
                            const len0 = data4.length;
                            for (let i0 = 0; i0 < len0; i0++) {
                              let data5 = data4[i0];
                              const _errs13 = errors;
                              const _errs14 = errors;
                              if (errors === _errs14) {
                                if (
                                  data5 &&
                                  typeof data5 == "object" &&
                                  !Array.isArray(data5)
                                ) {
                                  let missing1;
                                  if (
                                    (data5.entity_id === void 0 &&
                                      (missing1 = "entity_id")) ||
                                    (data5.name === void 0 &&
                                      (missing1 = "name")) ||
                                    (data5.state === void 0 &&
                                      (missing1 = "state")) ||
                                    (data5.source === void 0 &&
                                      (missing1 = "source")) ||
                                    (data5.observed_at === void 0 &&
                                      (missing1 = "observed_at")) ||
                                    (data5.last_updated === void 0 &&
                                      (missing1 = "last_updated")) ||
                                    (data5.attributes === void 0 &&
                                      (missing1 = "attributes")) ||
                                    (data5.capabilities === void 0 &&
                                      (missing1 = "capabilities")) ||
                                    (data5.remote_commands === void 0 &&
                                      (missing1 = "remote_commands")) ||
                                    (data5.power_on === void 0 &&
                                      (missing1 = "power_on")) ||
                                    (data5.power_off === void 0 &&
                                      (missing1 = "power_off"))
                                  ) {
                                    validate20.errors = [
                                      {
                                        instancePath:
                                          instancePath + "/home/" + i0,
                                        schemaPath:
                                          "#/$defs/BrowserHome/required",
                                        keyword: "required",
                                        params: { missingProperty: missing1 },
                                        message:
                                          "must have required property '" +
                                          missing1 +
                                          "'",
                                      },
                                    ];
                                    return false;
                                  } else {
                                    const _errs16 = errors;
                                    for (const key1 in data5) {
                                      if (
                                        !func1.call(schema42.properties, key1)
                                      ) {
                                        validate20.errors = [
                                          {
                                            instancePath:
                                              instancePath + "/home/" + i0,
                                            schemaPath:
                                              "#/$defs/BrowserHome/additionalProperties",
                                            keyword: "additionalProperties",
                                            params: {
                                              additionalProperty: key1,
                                            },
                                            message:
                                              "must NOT have additional properties",
                                          },
                                        ];
                                        return false;
                                        break;
                                      }
                                    }
                                    if (_errs16 === errors) {
                                      if (data5.attributes !== void 0) {
                                        let data6 = data5.attributes;
                                        const _errs17 = errors;
                                        if (errors === _errs17) {
                                          if (
                                            data6 &&
                                            typeof data6 == "object" &&
                                            !Array.isArray(data6)
                                          ) {
                                          } else {
                                            validate20.errors = [
                                              {
                                                instancePath:
                                                  instancePath +
                                                  "/home/" +
                                                  i0 +
                                                  "/attributes",
                                                schemaPath:
                                                  "#/$defs/BrowserHome/properties/attributes/type",
                                                keyword: "type",
                                                params: { type: "object" },
                                                message: "must be object",
                                              },
                                            ];
                                            return false;
                                          }
                                        }
                                        var valid4 = _errs17 === errors;
                                      } else {
                                        var valid4 = true;
                                      }
                                      if (valid4) {
                                        if (data5.capabilities !== void 0) {
                                          let data7 = data5.capabilities;
                                          const _errs20 = errors;
                                          if (errors === _errs20) {
                                            if (Array.isArray(data7)) {
                                              var valid5 = true;
                                              const len1 = data7.length;
                                              for (
                                                let i1 = 0;
                                                i1 < len1;
                                                i1++
                                              ) {
                                                const _errs22 = errors;
                                                if (
                                                  typeof data7[i1] !== "string"
                                                ) {
                                                  validate20.errors = [
                                                    {
                                                      instancePath:
                                                        instancePath +
                                                        "/home/" +
                                                        i0 +
                                                        "/capabilities/" +
                                                        i1,
                                                      schemaPath:
                                                        "#/$defs/BrowserHome/properties/capabilities/items/type",
                                                      keyword: "type",
                                                      params: {
                                                        type: "string",
                                                      },
                                                      message: "must be string",
                                                    },
                                                  ];
                                                  return false;
                                                }
                                                var valid5 = _errs22 === errors;
                                                if (!valid5) {
                                                  break;
                                                }
                                              }
                                            } else {
                                              validate20.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/home/" +
                                                    i0 +
                                                    "/capabilities",
                                                  schemaPath:
                                                    "#/$defs/BrowserHome/properties/capabilities/type",
                                                  keyword: "type",
                                                  params: { type: "array" },
                                                  message: "must be array",
                                                },
                                              ];
                                              return false;
                                            }
                                          }
                                          var valid4 = _errs20 === errors;
                                        } else {
                                          var valid4 = true;
                                        }
                                        if (valid4) {
                                          if (data5.entity_id !== void 0) {
                                            const _errs24 = errors;
                                            if (
                                              typeof data5.entity_id !==
                                              "string"
                                            ) {
                                              validate20.errors = [
                                                {
                                                  instancePath:
                                                    instancePath +
                                                    "/home/" +
                                                    i0 +
                                                    "/entity_id",
                                                  schemaPath:
                                                    "#/$defs/BrowserHome/properties/entity_id/type",
                                                  keyword: "type",
                                                  params: { type: "string" },
                                                  message: "must be string",
                                                },
                                              ];
                                              return false;
                                            }
                                            var valid4 = _errs24 === errors;
                                          } else {
                                            var valid4 = true;
                                          }
                                          if (valid4) {
                                            if (data5.last_updated !== void 0) {
                                              let data10 = data5.last_updated;
                                              const _errs26 = errors;
                                              const _errs27 = errors;
                                              let valid6 = false;
                                              const _errs28 = errors;
                                              if (typeof data10 !== "string") {
                                                const err2 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/home/" +
                                                    i0 +
                                                    "/last_updated",
                                                  schemaPath:
                                                    "#/$defs/BrowserHome/properties/last_updated/anyOf/0/type",
                                                  keyword: "type",
                                                  params: { type: "string" },
                                                  message: "must be string",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err2];
                                                } else {
                                                  vErrors.push(err2);
                                                }
                                                errors++;
                                              }
                                              var _valid1 = _errs28 === errors;
                                              valid6 = valid6 || _valid1;
                                              const _errs30 = errors;
                                              if (data10 !== null) {
                                                const err3 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/home/" +
                                                    i0 +
                                                    "/last_updated",
                                                  schemaPath:
                                                    "#/$defs/BrowserHome/properties/last_updated/anyOf/1/type",
                                                  keyword: "type",
                                                  params: { type: "null" },
                                                  message: "must be null",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err3];
                                                } else {
                                                  vErrors.push(err3);
                                                }
                                                errors++;
                                              }
                                              var _valid1 = _errs30 === errors;
                                              valid6 = valid6 || _valid1;
                                              if (!valid6) {
                                                const err4 = {
                                                  instancePath:
                                                    instancePath +
                                                    "/home/" +
                                                    i0 +
                                                    "/last_updated",
                                                  schemaPath:
                                                    "#/$defs/BrowserHome/properties/last_updated/anyOf",
                                                  keyword: "anyOf",
                                                  params: {},
                                                  message:
                                                    "must match a schema in anyOf",
                                                };
                                                if (vErrors === null) {
                                                  vErrors = [err4];
                                                } else {
                                                  vErrors.push(err4);
                                                }
                                                errors++;
                                                validate20.errors = vErrors;
                                                return false;
                                              } else {
                                                errors = _errs27;
                                                if (vErrors !== null) {
                                                  if (_errs27) {
                                                    vErrors.length = _errs27;
                                                  } else {
                                                    vErrors = null;
                                                  }
                                                }
                                              }
                                              var valid4 = _errs26 === errors;
                                            } else {
                                              var valid4 = true;
                                            }
                                            if (valid4) {
                                              if (data5.name !== void 0) {
                                                let data11 = data5.name;
                                                const _errs32 = errors;
                                                if (errors === _errs32) {
                                                  if (
                                                    typeof data11 === "string"
                                                  ) {
                                                    if (func2(data11) > 160) {
                                                      validate20.errors = [
                                                        {
                                                          instancePath:
                                                            instancePath +
                                                            "/home/" +
                                                            i0 +
                                                            "/name",
                                                          schemaPath:
                                                            "#/$defs/BrowserHome/properties/name/maxLength",
                                                          keyword: "maxLength",
                                                          params: {
                                                            limit: 160,
                                                          },
                                                          message:
                                                            "must NOT have more than 160 characters",
                                                        },
                                                      ];
                                                      return false;
                                                    }
                                                  } else {
                                                    validate20.errors = [
                                                      {
                                                        instancePath:
                                                          instancePath +
                                                          "/home/" +
                                                          i0 +
                                                          "/name",
                                                        schemaPath:
                                                          "#/$defs/BrowserHome/properties/name/type",
                                                        keyword: "type",
                                                        params: {
                                                          type: "string",
                                                        },
                                                        message:
                                                          "must be string",
                                                      },
                                                    ];
                                                    return false;
                                                  }
                                                }
                                                var valid4 = _errs32 === errors;
                                              } else {
                                                var valid4 = true;
                                              }
                                              if (valid4) {
                                                if (
                                                  data5.observed_at !== void 0
                                                ) {
                                                  let data12 =
                                                    data5.observed_at;
                                                  const _errs34 = errors;
                                                  if (errors === _errs34) {
                                                    if (errors === _errs34) {
                                                      if (
                                                        typeof data12 ===
                                                        "string"
                                                      ) {
                                                        if (
                                                          !formats2.validate(
                                                            data12,
                                                          )
                                                        ) {
                                                          validate20.errors = [
                                                            {
                                                              instancePath:
                                                                instancePath +
                                                                "/home/" +
                                                                i0 +
                                                                "/observed_at",
                                                              schemaPath:
                                                                "#/$defs/BrowserHome/properties/observed_at/format",
                                                              keyword: "format",
                                                              params: {
                                                                format:
                                                                  "date-time",
                                                              },
                                                              message:
                                                                'must match format "date-time"',
                                                            },
                                                          ];
                                                          return false;
                                                        }
                                                      } else {
                                                        validate20.errors = [
                                                          {
                                                            instancePath:
                                                              instancePath +
                                                              "/home/" +
                                                              i0 +
                                                              "/observed_at",
                                                            schemaPath:
                                                              "#/$defs/BrowserHome/properties/observed_at/type",
                                                            keyword: "type",
                                                            params: {
                                                              type: "string",
                                                            },
                                                            message:
                                                              "must be string",
                                                          },
                                                        ];
                                                        return false;
                                                      }
                                                    }
                                                  }
                                                  var valid4 =
                                                    _errs34 === errors;
                                                } else {
                                                  var valid4 = true;
                                                }
                                                if (valid4) {
                                                  if (
                                                    data5.power_off !== void 0
                                                  ) {
                                                    const _errs36 = errors;
                                                    if (
                                                      typeof data5.power_off !==
                                                      "boolean"
                                                    ) {
                                                      validate20.errors = [
                                                        {
                                                          instancePath:
                                                            instancePath +
                                                            "/home/" +
                                                            i0 +
                                                            "/power_off",
                                                          schemaPath:
                                                            "#/$defs/BrowserHome/properties/power_off/type",
                                                          keyword: "type",
                                                          params: {
                                                            type: "boolean",
                                                          },
                                                          message:
                                                            "must be boolean",
                                                        },
                                                      ];
                                                      return false;
                                                    }
                                                    var valid4 =
                                                      _errs36 === errors;
                                                  } else {
                                                    var valid4 = true;
                                                  }
                                                  if (valid4) {
                                                    if (
                                                      data5.power_on !== void 0
                                                    ) {
                                                      const _errs38 = errors;
                                                      if (
                                                        typeof data5.power_on !==
                                                        "boolean"
                                                      ) {
                                                        validate20.errors = [
                                                          {
                                                            instancePath:
                                                              instancePath +
                                                              "/home/" +
                                                              i0 +
                                                              "/power_on",
                                                            schemaPath:
                                                              "#/$defs/BrowserHome/properties/power_on/type",
                                                            keyword: "type",
                                                            params: {
                                                              type: "boolean",
                                                            },
                                                            message:
                                                              "must be boolean",
                                                          },
                                                        ];
                                                        return false;
                                                      }
                                                      var valid4 =
                                                        _errs38 === errors;
                                                    } else {
                                                      var valid4 = true;
                                                    }
                                                    if (valid4) {
                                                      if (
                                                        data5.remote_commands !==
                                                        void 0
                                                      ) {
                                                        let data15 =
                                                          data5.remote_commands;
                                                        const _errs40 = errors;
                                                        if (
                                                          errors === _errs40
                                                        ) {
                                                          if (
                                                            Array.isArray(
                                                              data15,
                                                            )
                                                          ) {
                                                            var valid7 = true;
                                                            const len2 =
                                                              data15.length;
                                                            for (
                                                              let i2 = 0;
                                                              i2 < len2;
                                                              i2++
                                                            ) {
                                                              const _errs42 =
                                                                errors;
                                                              if (
                                                                typeof data15[
                                                                  i2
                                                                ] !== "string"
                                                              ) {
                                                                validate20.errors =
                                                                  [
                                                                    {
                                                                      instancePath:
                                                                        instancePath +
                                                                        "/home/" +
                                                                        i0 +
                                                                        "/remote_commands/" +
                                                                        i2,
                                                                      schemaPath:
                                                                        "#/$defs/BrowserHome/properties/remote_commands/items/type",
                                                                      keyword:
                                                                        "type",
                                                                      params: {
                                                                        type: "string",
                                                                      },
                                                                      message:
                                                                        "must be string",
                                                                    },
                                                                  ];
                                                                return false;
                                                              }
                                                              var valid7 =
                                                                _errs42 ===
                                                                errors;
                                                              if (!valid7) {
                                                                break;
                                                              }
                                                            }
                                                          } else {
                                                            validate20.errors =
                                                              [
                                                                {
                                                                  instancePath:
                                                                    instancePath +
                                                                    "/home/" +
                                                                    i0 +
                                                                    "/remote_commands",
                                                                  schemaPath:
                                                                    "#/$defs/BrowserHome/properties/remote_commands/type",
                                                                  keyword:
                                                                    "type",
                                                                  params: {
                                                                    type: "array",
                                                                  },
                                                                  message:
                                                                    "must be array",
                                                                },
                                                              ];
                                                            return false;
                                                          }
                                                        }
                                                        var valid4 =
                                                          _errs40 === errors;
                                                      } else {
                                                        var valid4 = true;
                                                      }
                                                      if (valid4) {
                                                        if (
                                                          data5.source !==
                                                          void 0
                                                        ) {
                                                          let data17 =
                                                            data5.source;
                                                          const _errs44 =
                                                            errors;
                                                          if (
                                                            typeof data17 !==
                                                            "string"
                                                          ) {
                                                            validate20.errors =
                                                              [
                                                                {
                                                                  instancePath:
                                                                    instancePath +
                                                                    "/home/" +
                                                                    i0 +
                                                                    "/source",
                                                                  schemaPath:
                                                                    "#/$defs/BrowserHome/properties/source/type",
                                                                  keyword:
                                                                    "type",
                                                                  params: {
                                                                    type: "string",
                                                                  },
                                                                  message:
                                                                    "must be string",
                                                                },
                                                              ];
                                                            return false;
                                                          }
                                                          if (
                                                            "home-assistant" !==
                                                            data17
                                                          ) {
                                                            validate20.errors =
                                                              [
                                                                {
                                                                  instancePath:
                                                                    instancePath +
                                                                    "/home/" +
                                                                    i0 +
                                                                    "/source",
                                                                  schemaPath:
                                                                    "#/$defs/BrowserHome/properties/source/const",
                                                                  keyword:
                                                                    "const",
                                                                  params: {
                                                                    allowedValue:
                                                                      "home-assistant",
                                                                  },
                                                                  message:
                                                                    "must be equal to constant",
                                                                },
                                                              ];
                                                            return false;
                                                          }
                                                          var valid4 =
                                                            _errs44 === errors;
                                                        } else {
                                                          var valid4 = true;
                                                        }
                                                        if (valid4) {
                                                          if (
                                                            data5.state !==
                                                            void 0
                                                          ) {
                                                            let data18 =
                                                              data5.state;
                                                            const _errs46 =
                                                              errors;
                                                            if (
                                                              errors === _errs46
                                                            ) {
                                                              if (
                                                                typeof data18 ===
                                                                "string"
                                                              ) {
                                                                if (
                                                                  func2(
                                                                    data18,
                                                                  ) > 160
                                                                ) {
                                                                  validate20.errors =
                                                                    [
                                                                      {
                                                                        instancePath:
                                                                          instancePath +
                                                                          "/home/" +
                                                                          i0 +
                                                                          "/state",
                                                                        schemaPath:
                                                                          "#/$defs/BrowserHome/properties/state/maxLength",
                                                                        keyword:
                                                                          "maxLength",
                                                                        params:
                                                                          {
                                                                            limit: 160,
                                                                          },
                                                                        message:
                                                                          "must NOT have more than 160 characters",
                                                                      },
                                                                    ];
                                                                  return false;
                                                                }
                                                              } else {
                                                                validate20.errors =
                                                                  [
                                                                    {
                                                                      instancePath:
                                                                        instancePath +
                                                                        "/home/" +
                                                                        i0 +
                                                                        "/state",
                                                                      schemaPath:
                                                                        "#/$defs/BrowserHome/properties/state/type",
                                                                      keyword:
                                                                        "type",
                                                                      params: {
                                                                        type: "string",
                                                                      },
                                                                      message:
                                                                        "must be string",
                                                                    },
                                                                  ];
                                                                return false;
                                                              }
                                                            }
                                                            var valid4 =
                                                              _errs46 ===
                                                              errors;
                                                          } else {
                                                            var valid4 = true;
                                                          }
                                                        }
                                                      }
                                                    }
                                                  }
                                                }
                                              }
                                            }
                                          }
                                        }
                                      }
                                    }
                                  }
                                } else {
                                  validate20.errors = [
                                    {
                                      instancePath:
                                        instancePath + "/home/" + i0,
                                      schemaPath: "#/$defs/BrowserHome/type",
                                      keyword: "type",
                                      params: { type: "object" },
                                      message: "must be object",
                                    },
                                  ];
                                  return false;
                                }
                              }
                              var valid2 = _errs13 === errors;
                              if (!valid2) {
                                break;
                              }
                            }
                          } else {
                            validate20.errors = [
                              {
                                instancePath: instancePath + "/home",
                                schemaPath: "#/properties/home/type",
                                keyword: "type",
                                params: { type: "array" },
                                message: "must be array",
                              },
                            ];
                            return false;
                          }
                        }
                        var valid0 = _errs11 === errors;
                      } else {
                        var valid0 = true;
                      }
                      if (valid0) {
                        if (data.model !== void 0) {
                          let data19 = data.model;
                          const _errs48 = errors;
                          const _errs49 = errors;
                          let valid8 = false;
                          const _errs50 = errors;
                          if (typeof data19 !== "string") {
                            const err5 = {
                              instancePath: instancePath + "/model",
                              schemaPath: "#/properties/model/anyOf/0/type",
                              keyword: "type",
                              params: { type: "string" },
                              message: "must be string",
                            };
                            if (vErrors === null) {
                              vErrors = [err5];
                            } else {
                              vErrors.push(err5);
                            }
                            errors++;
                          }
                          var _valid2 = _errs50 === errors;
                          valid8 = valid8 || _valid2;
                          const _errs52 = errors;
                          if (data19 !== null) {
                            const err6 = {
                              instancePath: instancePath + "/model",
                              schemaPath: "#/properties/model/anyOf/1/type",
                              keyword: "type",
                              params: { type: "null" },
                              message: "must be null",
                            };
                            if (vErrors === null) {
                              vErrors = [err6];
                            } else {
                              vErrors.push(err6);
                            }
                            errors++;
                          }
                          var _valid2 = _errs52 === errors;
                          valid8 = valid8 || _valid2;
                          if (!valid8) {
                            const err7 = {
                              instancePath: instancePath + "/model",
                              schemaPath: "#/properties/model/anyOf",
                              keyword: "anyOf",
                              params: {},
                              message: "must match a schema in anyOf",
                            };
                            if (vErrors === null) {
                              vErrors = [err7];
                            } else {
                              vErrors.push(err7);
                            }
                            errors++;
                            validate20.errors = vErrors;
                            return false;
                          } else {
                            errors = _errs49;
                            if (vErrors !== null) {
                              if (_errs49) {
                                vErrors.length = _errs49;
                              } else {
                                vErrors = null;
                              }
                            }
                          }
                          var valid0 = _errs48 === errors;
                        } else {
                          var valid0 = true;
                        }
                        if (valid0) {
                          if (data.provider !== void 0) {
                            const _errs54 = errors;
                            if (typeof data.provider !== "string") {
                              validate20.errors = [
                                {
                                  instancePath: instancePath + "/provider",
                                  schemaPath: "#/properties/provider/type",
                                  keyword: "type",
                                  params: { type: "string" },
                                  message: "must be string",
                                },
                              ];
                              return false;
                            }
                            var valid0 = _errs54 === errors;
                          } else {
                            var valid0 = true;
                          }
                          if (valid0) {
                            if (data.reset !== void 0) {
                              const _errs56 = errors;
                              if (typeof data.reset !== "boolean") {
                                validate20.errors = [
                                  {
                                    instancePath: instancePath + "/reset",
                                    schemaPath: "#/properties/reset/type",
                                    keyword: "type",
                                    params: { type: "boolean" },
                                    message: "must be boolean",
                                  },
                                ];
                                return false;
                              }
                              var valid0 = _errs56 === errors;
                            } else {
                              var valid0 = true;
                            }
                            if (valid0) {
                              if (data.server_time !== void 0) {
                                const _errs58 = errors;
                                if (typeof data.server_time !== "string") {
                                  validate20.errors = [
                                    {
                                      instancePath:
                                        instancePath + "/server_time",
                                      schemaPath:
                                        "#/properties/server_time/type",
                                      keyword: "type",
                                      params: { type: "string" },
                                      message: "must be string",
                                    },
                                  ];
                                  return false;
                                }
                                var valid0 = _errs58 === errors;
                              } else {
                                var valid0 = true;
                              }
                              if (valid0) {
                                if (data.session !== void 0) {
                                  const _errs60 = errors;
                                  if (
                                    !validate28(data.session, {
                                      instancePath: instancePath + "/session",
                                      parentData: data,
                                      parentDataProperty: "session",
                                      rootData,
                                      dynamicAnchors,
                                    })
                                  ) {
                                    vErrors =
                                      vErrors === null
                                        ? validate28.errors
                                        : vErrors.concat(validate28.errors);
                                    errors = vErrors.length;
                                  }
                                  var valid0 = _errs60 === errors;
                                } else {
                                  var valid0 = true;
                                }
                                if (valid0) {
                                  if (data.version !== void 0) {
                                    let data24 = data.version;
                                    const _errs61 = errors;
                                    if (
                                      !(
                                        typeof data24 == "number" &&
                                        !(data24 % 1) &&
                                        !isNaN(data24)
                                      )
                                    ) {
                                      validate20.errors = [
                                        {
                                          instancePath:
                                            instancePath + "/version",
                                          schemaPath:
                                            "#/properties/version/type",
                                          keyword: "type",
                                          params: { type: "integer" },
                                          message: "must be integer",
                                        },
                                      ];
                                      return false;
                                    }
                                    if (1 !== data24) {
                                      validate20.errors = [
                                        {
                                          instancePath:
                                            instancePath + "/version",
                                          schemaPath:
                                            "#/properties/version/const",
                                          keyword: "const",
                                          params: { allowedValue: 1 },
                                          message: "must be equal to constant",
                                        },
                                      ];
                                      return false;
                                    }
                                    var valid0 = _errs61 === errors;
                                  } else {
                                    var valid0 = true;
                                  }
                                  if (valid0) {
                                    if (data.voice !== void 0) {
                                      const _errs63 = errors;
                                      if (
                                        !validate30(data.voice, {
                                          instancePath: instancePath + "/voice",
                                          parentData: data,
                                          parentDataProperty: "voice",
                                          rootData,
                                          dynamicAnchors,
                                        })
                                      ) {
                                        vErrors =
                                          vErrors === null
                                            ? validate30.errors
                                            : vErrors.concat(validate30.errors);
                                        errors = vErrors.length;
                                      }
                                      var valid0 = _errs63 === errors;
                                    } else {
                                      var valid0 = true;
                                    }
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        } else {
          validate20.errors = [
            {
              instancePath,
              schemaPath: "#/type",
              keyword: "type",
              params: { type: "object" },
              message: "must be object",
            },
          ];
          return false;
        }
      }
      validate20.errors = vErrors;
      return errors === 0;
    }
    validate20.evaluated = {
      props: true,
      dynamicProps: false,
      dynamicItems: false,
    };
  },
});
export default require_browser_validator();
