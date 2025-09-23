// swift-tools-version:5.5
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "CallDNS",
    platforms: [
        .iOS(.v13),
        .macOS(.v10_15),
        .watchOS(.v6),
        .tvOS(.v13)
    ],
    products: [
        .library(
            name: "CallDNS",
            targets: ["CallDNS"]
        ),
    ],
    dependencies: [
        .package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.8.0"),
        .package(url: "https://github.com/krzyzanowskim/CryptoSwift.git", from: "1.8.0")
    ],
    targets: [
        .target(
            name: "CallDNS",
            dependencies: [
                "Alamofire",
                "CryptoSwift"
            ],
            path: "Sources/CallDNS"
        ),
        .testTarget(
            name: "CallDNSTests",
            dependencies: ["CallDNS"],
            path: "Tests/CallDNSTests"
        ),
    ]
)