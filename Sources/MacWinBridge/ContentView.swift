import SwiftUI
import BridgeCore

struct ContentView: View {
    @ObservedObject var model: BridgeModel
    private let accent = Color(red: 0.35, green: 0.82, blue: 0.71)

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 26) {
                Label("MACWIN", systemImage: "point.3.connected.trianglepath.dotted")
                    .font(.system(size: 18, weight: .bold, design: .rounded)).foregroundStyle(accent)
                VStack(alignment: .leading, spacing: 6) {
                    Text("คลังเกม").font(.caption).foregroundStyle(.secondary)
                    ForEach(GameProfile.allCases) { profile in
                        Button { model.selected = profile } label: {
                            HStack(spacing: 10) {
                                Image(systemName: profile == .world ? "globe.asia.australia.fill" : "sun.horizon.fill")
                                Text(profile.title).font(.system(size: 13, weight: .medium))
                                Spacer(minLength: 0)
                            }.padding(12).background(model.selected == profile ? accent.opacity(0.16) : .clear, in: RoundedRectangle(cornerRadius: 9))
                        }.buttonStyle(.plain).disabled(model.busy)
                    }
                }
                Spacer()
                Text("PERSONAL PREVIEW · 0.1").font(.system(size: 9, weight: .semibold, design: .monospaced)).foregroundStyle(.secondary)
                Button("การตั้งค่า", systemImage: "slider.horizontal.3") { model.showSettings = true }.buttonStyle(.plain)
                Text("Windows apps on your Mac").font(.caption2).foregroundStyle(.tertiary)
            }.padding(24).frame(width: 230).frame(maxHeight: .infinity).background(Color.black.opacity(0.22))
            ScrollView {
                VStack(alignment: .leading, spacing: 23) {
                    HStack {
                        Text("MONSTER HUNTER").font(.system(size: 11, weight: .bold, design: .monospaced)).tracking(2).foregroundStyle(accent)
                        Spacer()
                        Text("APPLE SILICON").font(.system(size: 10, weight: .medium, design: .monospaced)).foregroundStyle(.secondary)
                    }
                    VStack(alignment: .leading, spacing: 10) {
                        Text(model.selected.title).font(.system(size: 34, weight: .bold, design: .rounded))
                        Text("ใช้ Steam และคลังเกมชุดเดียวร่วมกันทุกเกม")
                            .font(.system(size: 14)).foregroundStyle(.secondary)
                    }
                    HStack(spacing: 12) {
                        statusCard("Wine", value: model.hasWine ? "พบ runtime" : "ยังไม่พบ runtime", ready: model.hasWine)
                        statusCard("Steam Windows", value: model.hasSteam ? "ติดตั้งแล้ว" : "ยังไม่ติดตั้ง", ready: model.hasSteam)
                        statusCard("ไฟล์เกม", value: model.gameState == .installed ? "ติดตั้งแล้ว" : "ยังไม่พร้อม", ready: model.gameState == .installed)
                    }
                    VStack(alignment: .leading, spacing: 16) {
                        Label("เริ่มจาก Steam", systemImage: "play.rectangle").font(.headline)
                        Text(model.hasSteam ? "เปิด Steam รออัปเดต แล้วล็อกอินด้วยบัญชีของคุณในหน้าต่าง Steam" : "ติดตั้ง Steam ครั้งเดียว ใช้ร่วมกันทุกเกม")
                            .font(.callout).foregroundStyle(.secondary)
                        if model.hasSteamUIWorkaround {
                            Text("ตรวจอัปเดต Steam และซ่อมตัวช่วยแสดงผลอัตโนมัติก่อนเปิด")
                                .font(.caption).foregroundStyle(accent)
                        }
                        HStack(spacing: 12) {
                            Button { model.perform(model.hasSteam ? .openSteam : .installSteam) } label: {
                                Label(model.hasSteam ? "เปิด Steam" : "ติดตั้ง Steam", systemImage: model.hasSteam ? "arrow.up.forward.app" : "arrow.down.circle")
                                    .padding(.horizontal, 9).padding(.vertical, 5)
                            }.buttonStyle(.borderedProminent).tint(accent).foregroundStyle(.black)
                                .disabled(model.locked || !model.hasWine || model.otherActive)
                            Button("ติดตั้งเกมผ่าน Steam") { model.perform(.installGame) }
                                .disabled(model.locked || !model.hasSteam || model.otherActive)
                            Button("ทดลองเปิดเกม", systemImage: "play.fill") { model.perform(.playGame) }
                                .disabled(model.locked || model.gameState != .installed || model.otherActive)
                        }
                    }.padding(22).frame(maxWidth: .infinity, alignment: .leading)
                        .background(.white.opacity(0.045), in: RoundedRectangle(cornerRadius: 14))
                    VStack(alignment: .leading, spacing: 9) {
                        Label("อยู่ระหว่างทดสอบความเข้ากันได้", systemImage: "wrench.and.screwdriver").foregroundStyle(.orange)
                        Text("ยังไม่ยืนยันกราฟิกและการเล่นจริงของเกมนี้ การพบไฟล์เกมหรือติดตั้ง Steam สำเร็จยังไม่ใช่ผลทดสอบเกม")
                            .font(.callout).foregroundStyle(.secondary)
                        Text(model.gameStateText).font(.caption).foregroundStyle(.secondary)
                    }
                    Divider()
                    VStack(alignment: .leading, spacing: 9) {
                        HStack {
                            Circle().fill(model.active.isEmpty ? Color.gray : accent).frame(width: 6, height: 6)
                            Text(model.sessionText).font(.caption)
                            Spacer()
                            if model.busy { ProgressView().controlSize(.small) }
                        }
                        Text(model.message).font(.caption).foregroundStyle(.secondary)
                        if model.otherActive { Text("ออกจากเกมและปิด Steam ในอีกโปรไฟล์ก่อนใช้งานโปรไฟล์นี้").font(.caption).foregroundStyle(.orange) }
                        if let error = model.configurationError ?? model.error { Text(error).font(.caption).foregroundStyle(.red).textSelection(.enabled) }
                        HStack {
                            Button("เปิด log", systemImage: "doc.text.magnifyingglass") { model.openLogs() }
                            Button("ตรวจสถานะใหม่", systemImage: "arrow.clockwise") { Task { await model.refresh() } }.disabled(model.checking)
                        }.buttonStyle(.link).font(.caption)
                    }
                }.padding(32)
            }
        }
        .background(Color(red: 0.075, green: 0.09, blue: 0.115))
        .preferredColorScheme(.dark)
        .task { while !Task.isCancelled { await model.refresh(); try? await Task.sleep(for: .seconds(4)) } }
        .sheet(isPresented: $model.showSettings) { settings }
    }
    private func statusCard(_ title: String, value: String, ready: Bool) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            Label(value, systemImage: ready ? "checkmark.circle.fill" : "circle.dashed").font(.system(size: 12, weight: .medium)).foregroundStyle(ready ? accent : .secondary)
        }.padding(16).frame(maxWidth: .infinity, alignment: .leading).background(.white.opacity(0.035), in: RoundedRectangle(cornerRadius: 12))
    }
    private var settings: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("การตั้งค่า MacWin Bridge").font(.title2.bold())
            Text("เกมทั้งหมดเก็บที่ var/Steam/steamapps ใช้ระบบร่วมกันโดยไม่สร้างสำเนาตามเกม").font(.callout).foregroundStyle(.secondary)
            pathRow("Wine executable", url: model.config.wine, kind: "wine")
            pathRow("โฟลเดอร์ข้อมูล", url: model.config.root, kind: "root")
            pathRow("ตัวติดตั้ง Steam", url: model.config.installer, kind: "installer")
            HStack { Spacer(); Button("เสร็จแล้ว") { model.showSettings = false }.keyboardShortcut(.defaultAction) }
        }.padding(28).frame(width: 600)
    }
    private func pathRow(_ label: String, url: URL, kind: String) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack { Text(label).font(.headline); Spacer(); Button("เลือก…") { model.choose(kind) }.disabled(!model.canChangeConfiguration) }
            Text(url.path).font(.caption.monospaced()).foregroundStyle(.secondary).textSelection(.enabled)
        }
    }
}
