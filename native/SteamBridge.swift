import AppKit

final class SteamBridgeDelegate: NSObject, NSApplicationDelegate {
    var worker: Process?
    var pendingQuit = false
    var finished = false
    var output = ""
    var displayName = "Steam Bridge"
    var project = URL(fileURLWithPath: "")

    func applicationDidFinishLaunching(_ notification: Notification) {
        // The desktop icon opens Steam directly. Keep only its session supervisor alive.
        NSApp.setActivationPolicy(.accessory)
        do {
            guard let url = Bundle.main.url(forResource: "project", withExtension: "json")
            else { throw NSError(domain: "ไม่พบตำแหน่งโปรเจกต์", code: 1) }
            let record = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: url))
            guard let path = record["project"] else { throw NSError(domain: "ไม่พบตำแหน่งโปรเจกต์", code: 1) }
            let zzz = record["game"] == "zzz"
            displayName = zzz ? "ZZZ Bridge" : "Steam Bridge"
            project = path.hasPrefix("/") ? URL(fileURLWithPath: path)
                : Bundle.main.bundleURL.appendingPathComponent(path).standardizedFileURL
            let process = Process()
            let pipe = Pipe()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            process.arguments = [project.appendingPathComponent(zzz ? "scripts/zzz_session.py" : "scripts/steam_session.py").path]
                + (!zzz && CommandLine.arguments.contains("--limbus") ? ["--limbus"] : [])
            process.standardOutput = pipe; process.standardError = pipe
            process.standardInput = FileHandle.nullDevice
            pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
                let data = handle.availableData
                guard !data.isEmpty else { handle.readabilityHandler = nil; return }
                let text = String(decoding: data, as: UTF8.self)
                DispatchQueue.main.async { self?.receive(text) }
            }
            process.terminationHandler = { [weak self] process in
                DispatchQueue.main.async { self?.ended(process.terminationStatus) }
            }
            worker = process
            try process.run()
        } catch { ended(1, error: error.localizedDescription) }
    }
    func receive(_ text: String) {
        output += text
    }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if finished { return .terminateNow }
        if !pendingQuit {
            pendingQuit = true
            if worker?.isRunning == true { worker?.terminate() }
            else { finished = true; return .terminateNow }
        }
        return .terminateLater
    }
    func ended(_ status: Int32, error: String? = nil) {
        finished = true
        if status != 0 {
            NSApp.activate(ignoringOtherApps: true)
            let alert = NSAlert()
            alert.messageText = displayName + " ต้องการตรวจสอบ"
            alert.informativeText = error ?? (output.contains("watch-error")
                ? "ตรวจจับหน้าต่าง Steam ไม่สำเร็จ จึงปิดโปรไฟล์แล้ว กรุณาตรวจ log ก่อนลองใหม่"
                : String(output.suffix(1800)))
            alert.runModal()
        }
        if pendingQuit { NSApp.reply(toApplicationShouldTerminate: true) }
        else { NSApp.terminate(nil) }
    }
}
let app = NSApplication.shared
let delegate = SteamBridgeDelegate()
app.delegate = delegate
app.run()
