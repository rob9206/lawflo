/**
 * Dynojet Power Core - Blowfish Key Extractor
 * 
 * Usage: frida -n "Power Core" -l extract_key.js
 *    or: frida -p <PID> -l extract_key.js
 * 
 * Then trigger any encryption operation in Power Core
 * (open a tune file, connect to device, etc.)
 */

var keysCaptured = [];
var startTime = new Date();

console.log("╔══════════════════════════════════════════════════════════════╗");
console.log("║       DYNOJET POWER CORE - BLOWFISH KEY EXTRACTOR           ║");
console.log("╚══════════════════════════════════════════════════════════════╝");
console.log("");
console.log("[*] Started at: " + startTime.toISOString());

function toHexString(buffer, length) {
    var result = "";
    var bytes = new Uint8Array(buffer);
    for (var i = 0; i < length && i < bytes.length; i++) {
        result += ("0" + bytes[i].toString(16)).slice(-2);
        if (i < length - 1) result += " ";
    }
    return result;
}

function toAsciiString(ptr, length) {
    var result = "";
    for (var i = 0; i < length; i++) {
        var byte = ptr.add(i).readU8();
        if (byte >= 0x20 && byte <= 0x7E) {
            result += String.fromCharCode(byte);
        } else {
            result += ".";
        }
    }
    return result;
}

function saveKey(keyBytes, keyLen, operation) {
    var keyHex = toHexString(keyBytes, keyLen);
    var keyAscii = "";
    var bytes = new Uint8Array(keyBytes);
    
    for (var i = 0; i < keyLen; i++) {
        if (bytes[i] >= 0x20 && bytes[i] <= 0x7E) {
            keyAscii += String.fromCharCode(bytes[i]);
        }
    }
    
    var keyInfo = {
        operation: operation,
        timestamp: new Date().toISOString(),
        keyLength: keyLen,
        keyHex: keyHex,
        keyAscii: keyAscii
    };
    
    // Check if we already captured this key
    var isDuplicate = keysCaptured.some(function(k) {
        return k.keyHex === keyHex;
    });
    
    if (!isDuplicate) {
        keysCaptured.push(keyInfo);
        return keyInfo;
    }
    return null;
}

function hookBlowfish() {
    var blowfishModule = null;
    
    try {
        blowfishModule = Process.getModuleByName("BLOWFISHLIB.dll");
    } catch (e) {
        console.log("[-] BLOWFISHLIB.dll not loaded yet, retrying in 1 second...");
        setTimeout(hookBlowfish, 1000);
        return;
    }
    
    console.log("[+] Found BLOWFISHLIB.dll at: " + blowfishModule.base);
    
    var encryptAddr = blowfishModule.getExportByName("Encrypt");
    var decryptAddr = blowfishModule.getExportByName("Decrypt");
    
    console.log("[+] Encrypt function: " + encryptAddr);
    console.log("[+] Decrypt function: " + decryptAddr);
    console.log("");
    console.log("[*] Hooks installed! Now trigger encryption in Power Core...");
    console.log("[*] (Open a tune file, connect to device, etc.)");
    console.log("");
    console.log("────────────────────────────────────────────────────────────────");
    
    // Hook Encrypt
    Interceptor.attach(encryptAddr, {
        onEnter: function(args) {
            var dataLen = args[1].toInt32();
            var keyPtr = args[2];
            var keyLen = args[3].toInt32();
            
            if (keyLen > 0 && keyLen <= 64) {
                var keyBytes = keyPtr.readByteArray(keyLen);
                var keyInfo = saveKey(keyBytes, keyLen, "ENCRYPT");
                
                if (keyInfo) {
                    console.log("");
                    console.log("╔══════════════════════════════════════════════════════════════╗");
                    console.log("║                    🔐 KEY CAPTURED!                          ║");
                    console.log("╠══════════════════════════════════════════════════════════════╣");
                    console.log("║ Operation:  ENCRYPT                                          ║");
                    console.log("║ Data Size:  " + dataLen + " bytes".padEnd(49) + "║");
                    console.log("║ Key Length: " + keyLen + " bytes (" + (keyLen * 8) + " bits)".padEnd(43) + "║");
                    console.log("╠══════════════════════════════════════════════════════════════╣");
                    console.log("║ KEY (ASCII):                                                 ║");
                    console.log("║ " + keyInfo.keyAscii.substring(0, 60).padEnd(61) + "║");
                    if (keyInfo.keyAscii.length > 60) {
                        console.log("║ " + keyInfo.keyAscii.substring(60).padEnd(61) + "║");
                    }
                    console.log("╠══════════════════════════════════════════════════════════════╣");
                    console.log("║ KEY (HEX):                                                   ║");
                    var hexLines = keyInfo.keyHex.match(/.{1,48}/g) || [];
                    hexLines.forEach(function(line) {
                        console.log("║ " + line.padEnd(61) + "║");
                    });
                    console.log("╚══════════════════════════════════════════════════════════════╝");
                    console.log("");
                }
            }
        }
    });
    
    // Hook Decrypt
    Interceptor.attach(decryptAddr, {
        onEnter: function(args) {
            var dataLen = args[1].toInt32();
            var keyPtr = args[2];
            var keyLen = args[3].toInt32();
            
            if (keyLen > 0 && keyLen <= 64) {
                var keyBytes = keyPtr.readByteArray(keyLen);
                var keyInfo = saveKey(keyBytes, keyLen, "DECRYPT");
                
                if (keyInfo) {
                    console.log("");
                    console.log("╔══════════════════════════════════════════════════════════════╗");
                    console.log("║                    🔐 KEY CAPTURED!                          ║");
                    console.log("╠══════════════════════════════════════════════════════════════╣");
                    console.log("║ Operation:  DECRYPT                                          ║");
                    console.log("║ Data Size:  " + dataLen + " bytes".padEnd(49) + "║");
                    console.log("║ Key Length: " + keyLen + " bytes (" + (keyLen * 8) + " bits)".padEnd(43) + "║");
                    console.log("╠══════════════════════════════════════════════════════════════╣");
                    console.log("║ KEY (ASCII):                                                 ║");
                    console.log("║ " + keyInfo.keyAscii.substring(0, 60).padEnd(61) + "║");
                    if (keyInfo.keyAscii.length > 60) {
                        console.log("║ " + keyInfo.keyAscii.substring(60).padEnd(61) + "║");
                    }
                    console.log("╠══════════════════════════════════════════════════════════════╣");
                    console.log("║ KEY (HEX):                                                   ║");
                    var hexLines = keyInfo.keyHex.match(/.{1,48}/g) || [];
                    hexLines.forEach(function(line) {
                        console.log("║ " + line.padEnd(61) + "║");
                    });
                    console.log("╚══════════════════════════════════════════════════════════════╝");
                    console.log("");
                }
            }
        }
    });
}

// Start hooking
hookBlowfish();

// Export function to get all captured keys
rpc.exports = {
    getKeys: function() {
        return keysCaptured;
    },
    getSummary: function() {
        return {
            startTime: startTime.toISOString(),
            keysFound: keysCaptured.length,
            keys: keysCaptured
        };
    }
};

