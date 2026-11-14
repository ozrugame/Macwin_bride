import Foundation
import Testing
import CryptoKit
@testable import BridgeCore

struct BridgeCoreTests {
    @Test func updatedSteamHelperIsDelegatedToManagedSessionForRepair() throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let c = config(root)
        for profile in GameProfile.allCases { try touch(c.steam(profile)); try touch(c.sessionScript) }
        let folder = c.steam(.world).deletingLastPathComponent()
        let helper = folder.appendingPathComponent("bin/cef/cef.win64/steamwebhelper.exe")
        let original = helper.deletingLastPathComponent().appendingPathComponent("steamwebhelper_real.exe")
        try touch(helper); try Data("wrapper".utf8).write(to: helper)
        try Data("original".utf8).write(to: original)
        let digest: (Data) -> String = { SHA256.hash(data: $0).map { String(format: "%02x", $0) }.joined() }
        let record = ["wrapperSHA256": digest(Data("wrapper".utf8)), "originalSHA256": digest(Data("original".utf8))]
        try JSONEncoder().encode(record).write(to: folder.appendingPathComponent(".macwin-webhelper.json"))
        #expect(try LaunchRequest.make(.openSteam, profile: .world, config: c).arguments == [c.sessionScript.path, "--root", c.root.path, "--wine", c.wine.path])
        #expect(try LaunchRequest.make(.installGame, profile: .world, config: c).arguments.suffix(2) == ["--install-app", "582010"])
        #expect(try LaunchRequest.make(.playGame, profile: .world, config: c).arguments.suffix(2) == ["--app-id", "582010"])
        #expect(try LaunchRequest.make(.openSteam, profile: .rise, config: c).arguments == LaunchRequest.make(.openSteam, profile: .world, config: c).arguments)
        #expect(try LaunchRequest.make(.initialize, profile: .world, config: c).executable.path == "/usr/bin/python3")
        #expect(try LaunchRequest.make(.installSteam, profile: .rise, config: c).executable.path == "/usr/bin/python3")
        try Data("Steam updated this file".utf8).write(to: helper)
        #expect(try LaunchRequest.make(.openSteam, profile: .world, config: c).executable.path == "/usr/bin/python3")
        try Data("wrapper".utf8).write(to: helper)
        try Data("changed original".utf8).write(to: original)
        #expect(try LaunchRequest.make(.openSteam, profile: .world, config: c).executable.path == "/usr/bin/python3")
    }

    @Test func helperValidationIsDelegatedWithoutChangingFiles() throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let c = config(root); try touch(c.steam(.world)); try touch(c.sessionScript)
        let marker = c.steam(.world).deletingLastPathComponent().appendingPathComponent(".macwin-webhelper.json")
        try Data("broken".utf8).write(to: marker)
        #expect(try LaunchRequest.make(.openSteam, profile: .world, config: c).executable.path == "/usr/bin/python3")
        #expect(try String(contentsOf: marker, encoding: .utf8) == "broken")
    }

    func temporary() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("Bridge tests \(UUID())")
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }
    func config(_ root: URL) -> BridgeConfiguration {
        BridgeConfiguration(wine: URL(fileURLWithPath: "/usr/bin/true"), root: root, installer: root.appendingPathComponent("Steam $(literal).exe"))
    }
    func touch(_ url: URL) throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data().write(to: url)
    }

    @Test func gameSelectionReusesOnePrefixAndRoutesOnlyAppID() throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let c = config(root)
        try touch(c.steam(.world)); try touch(c.sessionScript)
        let r = try LaunchRequest.make(.installGame, profile: .world, config: c)
        #expect(c.prefix(.world) == c.prefix(.rise))
        #expect(r.environment["WINEPREFIX"] == root.appendingPathComponent("prefixes/shared").path)
        #expect(r.arguments == [c.sessionScript.path, "--root", c.root.path, "--wine", c.wine.path, "--install-app", "582010"])
    }

    @Test func missingSharedSteamNeverCreatesAnotherInstallation() throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let c = config(root); try touch(c.installer)
        #expect(throws: (any Error).self) { try LaunchRequest.make(.installSteam, profile: .rise, config: c) }
        #expect(throws: (any Error).self) { try LaunchRequest.make(.initialize, profile: .world, config: c) }
        #expect(!FileManager.default.fileExists(atPath: c.prefix(.rise).path))
    }

    @Test func missingSteamAndRuntimeAreActionableErrors() throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        var c = config(root)
        #expect(throws: (any Error).self) { try LaunchRequest.make(.openSteam, profile: .world, config: c) }
        c.wine = root.appendingPathComponent("absent wine")
        #expect(throws: (any Error).self) { try LaunchRequest.make(.initialize, profile: .world, config: c) }
    }

    @Test func configurationRoundTripsAndCorruptionIsNotSilentlyReset() throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let c = config(root), url = root.appendingPathComponent("settings/config.json")
        try c.save(to: url)
        #expect(FileManager.default.fileExists(atPath: url.path))
        if FileManager.default.fileExists(atPath: url.path) { #expect(try BridgeConfiguration.load(from: url) == c) }
        let corrupt = root.appendingPathComponent("corrupt.json")
        try Data("broken".utf8).write(to: corrupt)
        #expect(throws: (any Error).self) { try BridgeConfiguration.load(from: corrupt) }
        #expect(try String(contentsOf: corrupt, encoding: .utf8) == "broken")
    }

    @Test func incompleteSteamDownloadIsNotInstalled() throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let file = root.appendingPathComponent("appmanifest_582010.acf")
        try Data("\"AppState\" { \"appid\" \"582010\" \"StateFlags\" \"1026\" \"installdir\" \"Monster Hunter World\" }".utf8).write(to: file)
        #expect(SteamState.installation(manifest: file, common: root, appID: "582010") == .downloading)
    }

    @Test func installedManifestRequiresMatchingAppAndRealDirectory() throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let file = root.appendingPathComponent("appmanifest_582010.acf")
        try Data("\"AppState\" { \"appid\" \"582010\" \"StateFlags\" \"4\" \"installdir\" \"Monster Hunter World\" }".utf8).write(to: file)
        #expect(SteamState.installation(manifest: file, common: root, appID: "582010") != .installed)
        try FileManager.default.createDirectory(at: root.appendingPathComponent("Monster Hunter World"), withIntermediateDirectories: true)
        #expect(SteamState.installation(manifest: file, common: root, appID: "582010") == .installed)
        #expect(SteamState.installation(manifest: file, common: root, appID: "1446780") != .installed)
    }

    @Test func activeSteamIsRecognizedAfterLauncherReturns() throws {
        let root = URL(fileURLWithPath: "/tmp/My Bridge")
        let c = config(root)
        let listing = "42 /tmp/My Bridge/prefixes/shared/drive_c/Program Files (x86)/Steam/steam.exe\n"
        #expect(SteamState.activeProfile(processListing: listing, config: c) == .world)
        #expect(SteamState.activeProfile(processListing: "99 /another/app", config: c) == nil)
    }

    @Test func processLoggingDoesNotDeadlockAndPreservesExitCode() async throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let log = root.appendingPathComponent("output.log")
        let request = LaunchRequest(executable: URL(fileURLWithPath: "/bin/sh"), arguments: ["-c", "i=0; while [ $i -lt 5000 ]; do echo 'long-output-abcdefghijklmnopqrstuvwxyz'; echo 'stderr-abcdefghijklmnopqrstuvwxyz' >&2; i=$((i+1)); done; exit 7"])
        let result = try await ProcessRunner.run(request, log: log)
        #expect(result.status == 7)
        #expect(FileManager.default.fileExists(atPath: log.path))
        if FileManager.default.fileExists(atPath: log.path) { #expect(try Data(contentsOf: log).count > 100_000) }
    }

    @Test func sessionProbeRecognizesLiveServerWithoutKillingIt() async throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        let script = root.appendingPathComponent("wineserver")
        try Data("#!/bin/sh\nexec /bin/sleep 5\n".utf8).write(to: script)
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: script.path)
        #expect(try await WineSession.isActive(server: script, prefix: root))
        #expect(try await !WineSession.isActive(server: URL(fileURLWithPath: "/usr/bin/true"), prefix: root))
    }

    @Test func failedSessionProbeIsNotReportedAsInactive() async throws {
        let root = try temporary(); defer { try? FileManager.default.removeItem(at: root) }
        await #expect(throws: (any Error).self) {
            try await WineSession.isActive(server: URL(fileURLWithPath: "/usr/bin/false"), prefix: root)
        }
    }
}
