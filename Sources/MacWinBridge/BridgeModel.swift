import AppKit
import SwiftUI
import BridgeCore

@MainActor final class BridgeModel: ObservableObject {
    @Published var selected: GameProfile = .world
    @Published var config: BridgeConfiguration
    @Published var busy = false
    @Published var checking = false
    @Published var message = "พร้อมตรวจสอบเครื่องและเปิด Steam"
    @Published var error: String?
    @Published var configurationError: String?
    @Published var active: Set<GameProfile> = []
    @Published var sessionKnown = false
    @Published var lastLog: URL?
    @Published var showSettings = false
    @Published var revision = 0
    let project: URL
    let settings: URL
    private var running: [RunningProcess] = []

    init(projectURL: URL? = nil) {
        var location = projectURL ?? URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        if projectURL == nil, let resource = Bundle.main.url(forResource: "project", withExtension: "json"),
           let data = try? Data(contentsOf: resource),
           let record = try? JSONDecoder().decode([String: String].self, from: data), let path = record["project"] {
            location = path.hasPrefix("/") ? URL(fileURLWithPath: path)
                : Bundle.main.bundleURL.appendingPathComponent(path).standardizedFileURL
        }
        project = location; settings = location.appendingPathComponent("var/config.json")
        config = .local(project: location)
        if FileManager.default.fileExists(atPath: settings.path) {
            do {
                config = try BridgeConfiguration.load(from: settings)
                if config.root.standardizedFileURL != location.appendingPathComponent("var").standardizedFileURL {
                    configurationError = "คลังกลางต้องอยู่ใน var ของโปรเจกต์นี้ กรุณาย้ายข้อมูลก่อนเปลี่ยน root"
                }
            }
            catch { configurationError = "อ่านการตั้งค่าเดิมไม่ได้: \(error.localizedDescription) — แก้ไฟล์ config.json ก่อนใช้งาน เพื่อไม่เขียนทับข้อมูลเดิม" }
        }
    }

    var hasWine: Bool { FileManager.default.isExecutableFile(atPath: config.wine.path) }
    var hasSteam: Bool { FileManager.default.fileExists(atPath: config.steam(selected).path) }
    var hasSteamUIWorkaround: Bool { FileManager.default.fileExists(atPath: SteamUIWorkaround.recordURL(steam: config.steam(selected)).path) }
    var gameState: SteamInstallation { SteamState.installation(profile: selected, config: config) }
    var otherActive: Bool { false }
    var locked: Bool { busy || checking || configurationError != nil }
    var canChangeConfiguration: Bool { !busy && !checking && sessionKnown && active.isEmpty && configurationError == nil }
    var sessionText: String {
        if !sessionKnown { return "กำลังตรวจสอบหรือยังไม่ทราบสถานะ Wine" }
        return active.isEmpty ? "ไม่มีเซสชัน Wine ทำงาน" : "Steam ชุดกลางกำลังทำงาน"
    }
    var gameStateText: String {
        switch gameState {
        case .missing: "ยังไม่พบไฟล์เกม"
        case .downloading: "ติดตั้งหรืออัปเดตยังไม่เสร็จ"
        case .installed: "พบไฟล์ติดตั้ง — ยังต้องทดสอบเล่นจริง"
        case .unknown: "ยังตรวจสถานะไฟล์เกมไม่ได้"
        }
    }

    @discardableResult func refresh() async -> Bool {
        guard !checking else { return false }
        sessionKnown = false
        checking = true; defer { checking = false; revision += 1 }
        var sessions: Set<GameProfile> = []
        guard hasWine else {
            if GameProfile.allCases.contains(where: { FileManager.default.fileExists(atPath: config.prefix($0).appendingPathComponent("system.reg").path) }) {
                error = "ไม่พบ Wine สำหรับตรวจเซสชันเดิม กรุณาคืนค่า runtime เดิมก่อนเปลี่ยนโฟลเดอร์"; return false
            }
            active = []; sessionKnown = true; return true
        }
        do {
            for profile in [GameProfile.world] {
                if FileManager.default.fileExists(atPath: config.prefix(profile).appendingPathComponent("system.reg").path),
                   try await WineSession.isActive(server: config.wine.deletingLastPathComponent().appendingPathComponent("wineserver"), prefix: config.prefix(profile), environment: config.wineEnvironment) {
                    sessions.insert(profile)
                }
            }
            active = sessions
            sessionKnown = true
            for job in running where !job.process.isRunning {
                if job.process.terminationStatus != 0 { error = "คำสั่งจบด้วยรหัส \(job.process.terminationStatus) — เปิด log เพื่อดูรายละเอียด"; lastLog = job.log }
            }
            running.removeAll { !$0.process.isRunning }
            return true
        } catch { self.error = error.localizedDescription; return false }
    }

    func perform(_ action: BridgeAction) {
        guard !locked else { return }
        busy = true; error = nil
        let profile = selected
        Task {
            defer { busy = false }
            guard await refresh() else { return }
            do {
                try config.save(to: settings)
                try FileManager.default.createDirectory(at: config.root, withIntermediateDirectories: true)
                try FileManager.default.createDirectory(at: config.prefix(profile).deletingLastPathComponent(), withIntermediateDirectories: true)
                let request = try LaunchRequest.make(action, profile: profile, config: config)
                let log = config.root.appendingPathComponent("logs/\(profile.rawValue)-\(action.rawValue)-\(UUID().uuidString).log")
                lastLog = log
                if (action == .initialize || action == .installSteam) && !hasSteam {
                    message = "กำลังเตรียม \(profile.title)… ขั้นตอนแรกอาจใช้เวลาสักครู่"
                    let result = try await ProcessRunner.run(request, log: log)
                    guard result.status == 0 else { throw BridgeError("คำสั่งจบด้วยรหัส \(result.status) — ตรวจ log") }
                    message = hasSteam ? "ติดตั้ง Steam แล้ว กดเปิด Steam เพื่ออัปเดตและล็อกอิน" : "สร้างโปรไฟล์แล้ว"
                } else {
                    let job = try ProcessRunner.start(request, log: log)
                    running.append(job)
                    message = "ส่งคำสั่งแล้ว — ตรวจหน้าต่าง Steam หรือเกมเพื่อยืนยันผล"
                }
                await refresh()
            } catch { self.error = error.localizedDescription }
        }
    }

    func choose(_ kind: String) {
        guard canChangeConfiguration else {
            error = "ต้องตรวจยืนยันว่า Steam และเกมปิดแล้ว ก่อนเปลี่ยนตำแหน่งข้อมูลหรือ Wine"; return
        }
        if kind == "root" {
            error = "คลังกลางอยู่ที่ var/Steam การย้ายคลังต้องย้ายไฟล์และทางลัดพร้อมกัน จึงยังเปลี่ยนโฟลเดอร์จากหน้านี้ไม่ได้"; return
        }
        let panel = NSOpenPanel()
        panel.canChooseDirectories = kind == "root"; panel.canChooseFiles = kind != "root"
        panel.allowsMultipleSelection = false
        panel.message = kind == "wine" ? "เลือกไฟล์ executable ชื่อ wine ภายใน runtime" : kind == "root" ? "เลือกโฟลเดอร์ข้อมูลใหม่ (ไม่ได้ย้ายเกมเดิม)" : "เลือก SteamSetup.exe จาก Valve"
        panel.showsHiddenFiles = true
        guard panel.runModal() == .OK, let url = panel.url else { return }
        var candidate = config
        switch kind { case "wine": candidate.wine = url; case "root": candidate.root = url; default: candidate.installer = url }
        busy = true
        Task {
            defer { busy = false }
            guard await refresh(), active.isEmpty else {
                error = "ยังยืนยันไม่ได้ว่าเซสชันเดิมปิดแล้ว จึงยังไม่เปลี่ยนการตั้งค่า"; return
            }
            do {
                try candidate.save(to: settings); config = candidate; error = nil; sessionKnown = false
                await refresh()
            } catch { self.error = error.localizedDescription }
        }
    }
    func openLogs() {
        if let lastLog { NSWorkspace.shared.activateFileViewerSelecting([lastLog]) }
        else { NSWorkspace.shared.open(config.root.appendingPathComponent("logs")) }
    }
}
