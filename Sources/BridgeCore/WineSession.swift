import Foundation

public enum WineSession {
    // `wineserver -w` waits for an existing server; it does not start or stop one.
    // Terminate only this short-lived observer when the session is still active.
    public static func isActive(server: URL, prefix: URL, environment: [String: String] = [:]) async throws -> Bool {
        try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .utility).async {
                let observer = Process()
                observer.executableURL = server; observer.arguments = ["-w"]
                observer.environment = ProcessInfo.processInfo.environment.merging(environment) { _, new in new }.merging(["WINEPREFIX": prefix.path]) { _, new in new }
                observer.standardOutput = FileHandle.nullDevice; observer.standardError = FileHandle.nullDevice
                do {
                    try observer.run()
                    for _ in 0..<8 {
                        if !observer.isRunning { break }
                        Thread.sleep(forTimeInterval: 0.05)
                    }
                    if observer.isRunning {
                        observer.terminate(); observer.waitUntilExit()
                        continuation.resume(returning: true)
                    } else {
                        observer.waitUntilExit()
                        guard observer.terminationStatus == 0 else { throw BridgeError("ตรวจสถานะ Wine ไม่สำเร็จ (\(observer.terminationStatus))") }
                        continuation.resume(returning: false)
                    }
                } catch { continuation.resume(throwing: error) }
            }
        }
    }
}
