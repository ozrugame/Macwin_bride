import Foundation
import CryptoKit

/// Only an explicitly registered, byte-verified helper may bypass Steam's size check.
public enum SteamUIWorkaround {
    public static func recordURL(steam: URL) -> URL {
        steam.deletingLastPathComponent().appendingPathComponent(".macwin-webhelper.json")
    }

    public static func launchArguments(steam: URL) throws -> [String] {
        let marker = recordURL(steam: steam)
        guard FileManager.default.fileExists(atPath: marker.path) else { return [] }
        struct Record: Decodable { let wrapperSHA256: String; let originalSHA256: String }
        do {
            let record = try JSONDecoder().decode(Record.self, from: Data(contentsOf: marker))
            let folder = steam.deletingLastPathComponent().appendingPathComponent("bin/cef/cef.win64")
            for (name, expected) in [("steamwebhelper.exe", record.wrapperSHA256), ("steamwebhelper_real.exe", record.originalSHA256)] {
                let bytes = try Data(contentsOf: folder.appendingPathComponent(name))
                let actual = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
                guard actual == expected else { throw BridgeError("Steam helper changed") }
            }
        } catch {
            throw BridgeError("ตัวช่วยแก้หน้าดำไม่ตรงกับรุ่นที่ตรวจไว้ อาจเกิดจาก Steam อัปเดต กรุณาปิด Steam แล้วตรวจหรือติดตั้งตัวช่วยใหม่ก่อนเปิดอีกครั้ง")
        }
        return ["-noverifyfiles"]
    }
}
