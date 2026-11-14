import Foundation
import BridgeCore

@main struct BridgeCLI {
    static func main() async {
        do {
            var args = Array(CommandLine.arguments.dropFirst())
            let command = args.isEmpty ? "doctor" : args.removeFirst()
            var profile = GameProfile.world
            var project = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            var rootOverride: URL?
            while !args.isEmpty {
                let key = args.removeFirst()
                guard !args.isEmpty else { throw BridgeError("Missing value for \(key)") }
                let value = args.removeFirst()
                switch key {
                case "--profile":
                    guard let p = GameProfile(rawValue: value) else { throw BridgeError("Profile must be world or rise") }
                    profile = p
                case "--project": project = URL(fileURLWithPath: value)
                case "--root": rootOverride = URL(fileURLWithPath: value)
                default: throw BridgeError("Unknown option: \(key)")
                }
            }
            let settings = project.appendingPathComponent("var/config.json")
            var config = FileManager.default.fileExists(atPath: settings.path)
                ? try BridgeConfiguration.load(from: settings) : .local(project: project)
            if let rootOverride, rootOverride.standardizedFileURL != project.appendingPathComponent("var").standardizedFileURL {
                throw BridgeError("ใช้คลังกลาง var ของโปรเจกต์นี้เท่านั้น การเปลี่ยน root ต้องย้ายข้อมูลก่อน")
            }
            if command == "doctor" || command == "status" {
                print("Wine: \(config.wine.path)")
                print("Executable present: \(FileManager.default.isExecutableFile(atPath: config.wine.path))")
                print("Profile: \(profile.title)")
                print("Prefix: \(config.prefix(profile).path)")
                print("Steam installed: \(FileManager.default.fileExists(atPath: config.steam(profile).path))")
                print("Game files: \(SteamState.installation(profile: profile, config: config).rawValue)")
                print("Game graphics/playability: not verified")
                return
            }
            let actions: [String: BridgeAction] = ["init": .initialize, "install-steam": .installSteam, "steam": .openSteam, "install-game": .installGame, "play": .playGame]
            guard let action = actions[command] else {
                throw BridgeError("Usage: bridge doctor|status|init|install-steam|steam|install-game|play [--profile world|rise] [--project PATH] [--root PATH]")
            }
            let request = try LaunchRequest.make(action, profile: profile, config: config)
            try FileManager.default.createDirectory(at: config.root, withIntermediateDirectories: true)
            try FileManager.default.createDirectory(at: config.prefix(profile).deletingLastPathComponent(), withIntermediateDirectories: true)
            let log = config.root.appendingPathComponent("logs/\(profile.rawValue)-\(command)-\(UUID().uuidString).log")
            print("Log: \(log.path)")
            if (action == .initialize || action == .installSteam) && !FileManager.default.fileExists(atPath: config.steam(profile).path) {
                let result = try await ProcessRunner.run(request, log: log)
                guard result.status == 0 else { throw BridgeError("Process exited \(result.status); inspect the log.") }
                print("Command completed. Game compatibility is not yet verified.")
            } else {
                let running = try ProcessRunner.start(request, log: log)
                print("Request submitted (PID \(running.process.processIdentifier)). Verify the Steam/game window.")
            }
        } catch {
            FileHandle.standardError.write(Data("Error: \(error.localizedDescription)\n".utf8)); exit(1)
        }
    }
}
