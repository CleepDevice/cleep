/**
 * This file contains javascript helpers
 */

/**
 * Append developer asset bust when the RPC shell injected __CLEEP_ASSET_BUST__.
 * Keeps lazy-loaded module URLs unique after each frontend sync.
 * @param {string} path
 * @returns {string}
 */
function cleepAssetUrl(path) {
    var bust = typeof window !== 'undefined' ? window.__CLEEP_ASSET_BUST__ : null;
    if (!bust || !path) {
        return path;
    }
    return path + (path.indexOf('?') >= 0 ? '&' : '?') + '_=' + encodeURIComponent(bust);
}

String.prototype.parseBool = function() {
    return (/^true$/i).test(this);
};

/**
 * http://jamesroberts.name/blog/2010/02/22/string-functions-for-javascript-trim-to-camel-case-to-dashed-and-to-underscore/
 * String functions
 */
String.prototype.toCamel = function() {
    return this.replace(/(\-[a-z])/g, function($1){return $1.toUpperCase().replace('-','');});
};

String.prototype.toKebab = function() {
    return this.replace(/([A-Z])/g, function($1){return "-"+$1.toLowerCase();});
};

String.prototype.toSnake = function() {
    return this.replace(/([A-Z])/g, function($1){return "_"+$1.toLowerCase();});
};

String.prototype.trim = function() {
    return this.replace(/^\s+|\s+$/g, "");
};

String.prototype.firstUpperCase = function() {
    return this.charAt(0).toUpperCase() + this.slice(1).toLowerCase();
};

