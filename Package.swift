// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MacWinBridge",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "BridgeCore", targets: ["BridgeCore"]),
        .executable(name: "bridge", targets: ["BridgeCLI"]),
        .executable(name: "MacWinBridge", targets: ["MacWinBridge"])
    ],
    targets: [
        .target(name: "BridgeCore"),
        .executableTarget(name: "BridgeCLI", dependencies: ["BridgeCore"]),
        .executableTarget(name: "MacWinBridge", dependencies: ["BridgeCore"]),
        .testTarget(name: "BridgeCoreTests", dependencies: ["BridgeCore"]),
        .testTarget(name: "BridgeModelTests", dependencies: ["BridgeCore", "MacWinBridge"])
    ]
)
