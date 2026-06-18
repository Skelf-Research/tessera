Pod::Spec.new do |spec|
  spec.name         = "Tessera"
  spec.version      = "0.1.0"
  spec.summary      = "Zero-knowledge caller verification for iOS"
  spec.description  = <<-DESC
    Tessera iOS SDK provides zero-knowledge proof verification for incoming calls
    of any type including voice calls, VoIP calls, in-app calls, and video calls.
    Protects against spoofing and deepfakes while maintaining privacy.
  DESC

  spec.homepage     = "https://github.com/dipankar/tessera"
  spec.license      = { :type => "MIT", :file => "LICENSE" }
  spec.author       = { "Dipankar Sarkar" => "me@dipankar.name" }

  spec.platform     = :ios, "13.0"
  spec.swift_version = "5.0"

  spec.source       = { :git => "https://github.com/dipankar/tessera.git", :tag => "#{spec.version}" }
  spec.source_files = "sdks/ios/Sources/Tessera/**/*.{swift,h,m}"

  spec.framework    = "Foundation", "UIKit", "SwiftUI", "CallKit", "Contacts"
  spec.dependency "CryptoSwift", "~> 1.8"
  spec.dependency "Alamofire", "~> 5.8"

  spec.requires_arc = true

  spec.test_spec 'Tests' do |test_spec|
    test_spec.source_files = 'sdks/ios/Tests/TesseraTests/**/*.{swift}'
  end
end