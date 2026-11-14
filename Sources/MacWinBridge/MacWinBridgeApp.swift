import SwiftUI
@main struct MacWinBridgeApp: App {
    @StateObject private var model = BridgeModel()
    var body: some Scene {
        WindowGroup("MacWin Bridge") { ContentView(model: model).frame(minWidth: 850, minHeight: 610) }
            .defaultSize(width: 980, height: 680)
    }
}
