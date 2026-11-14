import Foundation

public enum GameProfile: String, Codable, CaseIterable, Identifiable, Sendable {
    case world, rise
    public var id: String { rawValue }
    public var appID: String { self == .world ? "582010" : "1446780" }
    public var title: String { self == .world ? "World / Iceborne" : "Rise / Sunbreak" }
}

public struct BridgeConfiguration: Codable, Equatable, Sendable {
    public var wine: URL
    public var root: URL
    public var installer: URL
    public init(wine: URL, root: URL, installer: URL) {
        self.wine = wine; self.root = root; self.installer = installer
    }
    public func prefix(_ profile: GameProfile) -> URL { root.appendingPathComponent("prefixes/shared") }
    public func steam(_ profile: GameProfile) -> URL {
        prefix(profile).appendingPathComponent("drive_c/Program Files (x86)/Steam/Steam.exe")
    }
    public var sharedSteam: URL { root.appendingPathComponent("Steam") }
    public var sessionScript: URL { root.deletingLastPathComponent().appendingPathComponent("scripts/steam_session.py") }
    public var wineEnvironment: [String: String] {
        ["WINEPREFIX": prefix(.world).path, "WINEDEBUG": "fixme-all", "SikarugirAppWine11": "1",
         "WINEDLLOVERRIDES": "winemenubuilder.exe=d",
         "DYLD_FALLBACK_LIBRARY_PATH": wine.deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("lib").path + ":/Library/Frameworks/GStreamer.framework/Libraries:/usr/lib"]
    }
    public func save(to url: URL) throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(self).write(to: url, options: .atomic)
    }
    public static func load(from url: URL) throws -> Self {
        try JSONDecoder().decode(Self.self, from: Data(contentsOf: url))
    }
    public static func local(project: URL) -> Self {
        Self(wine: project.appendingPathComponent(".runtime/sikarugir/wswine.bundle/bin/wine"),
             root: project.appendingPathComponent("var"), installer: project.appendingPathComponent(".downloads/SteamSetup.exe"))
    }
}
