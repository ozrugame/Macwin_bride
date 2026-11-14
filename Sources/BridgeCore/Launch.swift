import Foundation

public enum BridgeAction: String, Sendable { case initialize, installSteam, openSteam, installGame, playGame }
public struct BridgeError: LocalizedError, Sendable {
    public let message: String
    public init(_ message: String) { self.message = message }
    public var errorDescription: String? { message }
}
public struct LaunchRequest: Sendable {
    public var executable: URL
    public var arguments: [String]
    public var environment: [String: String]
    public var workingDirectory: URL?
    public init(executable: URL, arguments: [String] = [], environment: [String: String] = [:], workingDirectory: URL? = nil) {
        self.executable = executable; self.arguments = arguments; self.environment = environment; self.workingDirectory = workingDirectory
    }
    public static func make(_ action: BridgeAction, profile: GameProfile, config: BridgeConfiguration) throws -> Self {
        guard FileManager.default.isExecutableFile(atPath: config.wine.path) else {
            throw BridgeError("ไม่พบ Wine ที่เปิดใช้งานได้: \(config.wine.path)")
        }
        let installed = FileManager.default.fileExists(atPath: config.steam(profile).path)
        if action == .openSteam || action == .installGame || action == .playGame || ((action == .installSteam || action == .initialize) && installed) {
            guard installed else { throw BridgeError("ยังไม่พบ Steam ในชุดกลาง") }
            // The managed session verifies/repairs the helper after Steam updates.
            guard FileManager.default.fileExists(atPath: config.sessionScript.path) else {
                throw BridgeError("ไม่พบตัวเปิดชุดกลาง กรุณาใช้โฟลเดอร์ข้อมูล var ของโปรเจกต์นี้")
            }
            var args = [config.sessionScript.path, "--root", config.root.path, "--wine", config.wine.path]
            if action == .installGame { args += ["--install-app", profile.appID] }
            if action == .playGame { args += ["--app-id", profile.appID] }
            return Self(executable: URL(fileURLWithPath: "/usr/bin/python3"), arguments: args,
                        environment: config.wineEnvironment, workingDirectory: config.root)
        }
        throw BridgeError("ยังไม่พบ Steam ชุดกลาง กรุณาซ่อมหรือย้ายคลังเดิมก่อน ไม่สร้าง Steam อีกชุดโดยอัตโนมัติ")
    }
}
public struct RunResult: Sendable { public let status: Int32; public let log: URL }
public final class RunningProcess: @unchecked Sendable {
    public let process: Process
    public let log: URL
    fileprivate let output: FileHandle
    fileprivate init(process: Process, log: URL, output: FileHandle) {
        self.process = process; self.log = log; self.output = output
    }
    deinit { try? output.close() }
}
public enum ProcessRunner {
    public static func start(_ request: LaunchRequest, log: URL) throws -> RunningProcess {
        try FileManager.default.createDirectory(at: log.deletingLastPathComponent(), withIntermediateDirectories: true)
        guard FileManager.default.createFile(atPath: log.path, contents: nil) else { throw BridgeError("สร้าง log ไม่สำเร็จ") }
        let output = try FileHandle(forWritingTo: log)
        let process = Process()
        process.executableURL = request.executable
        process.arguments = request.arguments
        process.environment = ProcessInfo.processInfo.environment.merging(request.environment) { _, new in new }
        process.currentDirectoryURL = request.workingDirectory
        process.standardOutput = output; process.standardError = output
        process.standardInput = FileHandle.nullDevice
        do { try process.run() } catch { try? output.close(); throw error }
        return RunningProcess(process: process, log: log, output: output)
    }
    public static func run(_ request: LaunchRequest, log: URL) async throws -> RunResult {
        try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                do {
                    let running = try start(request, log: log)
                    running.process.waitUntilExit()
                    try running.output.synchronize()
                    continuation.resume(returning: RunResult(status: running.process.terminationStatus, log: log))
                } catch { continuation.resume(throwing: error) }
            }
        }
    }
}
