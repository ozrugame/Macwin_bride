import Foundation

public enum SteamInstallation: String, Sendable { case missing, downloading, installed, unknown }
public enum SteamState {
    public static func installation(manifest: URL, common: URL, appID: String) -> SteamInstallation {
        guard FileManager.default.fileExists(atPath: manifest.path) else { return .missing }
        guard let text = try? String(contentsOf: manifest, encoding: .utf8) else { return .unknown }
        func value(_ key: String) -> String? {
            let pattern = "\"" + NSRegularExpression.escapedPattern(for: key) + "\"\\s*\"([^\"]*)\""
            guard let regex = try? NSRegularExpression(pattern: pattern),
                  let match = regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)),
                  let range = Range(match.range(at: 1), in: text) else { return nil }
            return String(text[range])
        }
        guard value("appid") == appID, let flags = value("StateFlags").flatMap(Int.init) else { return .unknown }
        guard flags == 4 else { return .downloading }
        guard let name = value("installdir"), !name.isEmpty, !name.contains("/"), !name.contains("\\"), name != ".." else { return .unknown }
        var directory: ObjCBool = false
        return FileManager.default.fileExists(atPath: common.appendingPathComponent(name).path, isDirectory: &directory) && directory.boolValue ? .installed : .missing
    }
    public static func activeProfile(processListing: String, config: BridgeConfiguration) -> GameProfile? {
        for profile in GameProfile.allCases {
            let prefix = config.prefix(profile).path.lowercased() + "/"
            if processListing.lowercased().split(separator: "\n").contains(where: { $0.contains(prefix) && ($0.contains("steam.exe") || $0.contains("steamwebhelper.exe")) }) {
                return profile
            }
        }
        return nil
    }
    public static func installation(profile: GameProfile, config: BridgeConfiguration) -> SteamInstallation {
        let apps = config.steam(profile).deletingLastPathComponent().appendingPathComponent("steamapps")
        return installation(manifest: apps.appendingPathComponent("appmanifest_\(profile.appID).acf"),
                            common: apps.appendingPathComponent("common"), appID: profile.appID)
    }
}
