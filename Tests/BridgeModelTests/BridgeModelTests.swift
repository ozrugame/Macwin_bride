import Foundation
import Testing
import BridgeCore
@testable import MacWinBridge

@MainActor struct BridgeModelTests {
    @Test func settingsStayLockedWhenSessionProbeFails() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("Bridge Model \(UUID())")
        defer { try? FileManager.default.removeItem(at: root) }
        let bin = root.appendingPathComponent("bin")
        try FileManager.default.createDirectory(at: bin, withIntermediateDirectories: true)
        let wine = bin.appendingPathComponent("wine"), server = bin.appendingPathComponent("wineserver")
        for url in [wine, server] {
            // A system executable avoids first-run script checks racing the 400ms probe.
            try FileManager.default.createSymbolicLink(at: url, withDestinationURL: URL(fileURLWithPath: "/usr/bin/false"))
        }
        let config = BridgeConfiguration(wine: wine, root: root.appendingPathComponent("var"), installer: root.appendingPathComponent("SteamSetup.exe"))
        try FileManager.default.createDirectory(at: config.prefix(.world), withIntermediateDirectories: true)
        try Data().write(to: config.prefix(.world).appendingPathComponent("system.reg"))
        try config.save(to: root.appendingPathComponent("var/config.json"))
        let model = BridgeModel(projectURL: root)
        #expect(await model.refresh() == false)
        #expect(model.error != nil)
        #expect(model.canChangeConfiguration == false)
    }
}
