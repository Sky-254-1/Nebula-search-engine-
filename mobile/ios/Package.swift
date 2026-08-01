// swift-tools-version:5.5
import PackageDescription

let package = Package(
    name: "NebulaMobile",
    platforms: [
        .iOS(.v14)
    ],
    dependencies: [
        .package(url: "https://github.com/ionic-team/capacitor-swift-package-manager.git", from: "1.0.0")
    ],
    targets: [
        .target(
            name: "NebulaMobile",
            dependencies: [
                .product(name: "Capacitor", package: "capacitor-swift-package-manager")
            ],
            path: "Sources"
        )
    ]
)
