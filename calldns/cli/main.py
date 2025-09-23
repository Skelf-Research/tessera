"""
CallDNS CLI main module.
Provides command-line interface for CallDNS operations.
"""

import argparse
import sys
import json
import time
from typing import List
from ..sdk import Caller, Verifier
from ..sdk.identity_manager import IdentityManager
from ..sdk.commitment_manager import CommitmentManager


def main():
    """Main entry point for the CallDNS CLI."""
    parser = argparse.ArgumentParser(
        prog='calldns',
        description='CallDNS - Zero-knowledge caller verification system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  verify     Verify an incoming call
  register   Register your identity
  call       Make a verified call
  identity   Manage your identity
  contacts   Manage contacts
  help       Show this help message
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='help',
        help='Command to execute'
    )
    
    parser.add_argument(
        'args',
        nargs=argparse.REMAINDER,
        help='Additional arguments for the command'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == 'verify':
        handle_verify_command(args.args)
    elif args.command == 'register':
        handle_register_command(args.args)
    elif args.command == 'call':
        handle_call_command(args.args)
    elif args.command == 'identity':
        handle_identity_command(args.args)
    elif args.command == 'contacts':
        handle_contacts_command(args.args)
    else:
        parser.print_help()


def handle_verify_command(args: List[str]):
    """Handle the verify command."""
    parser = argparse.ArgumentParser(description='Verify an incoming call')
    parser.add_argument('--proof', '-p', help='ZK proof to verify (JSON)')
    parser.add_argument('--commitment', '-c', help='Reception commitment ID')

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return

    print("🔍 Verifying incoming call...")

    try:
        verifier = Verifier()

        if parsed_args.proof:
            # Verify a specific proof
            try:
                proof_data = json.loads(parsed_args.proof)
                is_valid = verifier.verify_call_proof(proof_data)

                if is_valid:
                    print("✅ Call verification successful - Caller is authenticated")
                else:
                    print("❌ Call verification failed - Caller could not be authenticated")
            except json.JSONDecodeError:
                print("❌ Error: Invalid proof format. Please provide valid JSON.")
        else:
            # Interactive verification
            print("📞 Waiting for incoming call proof...")
            print("💡 Tip: Use --proof option to verify a specific proof")

            # Generate a sample reception commitment
            commitment_manager = CommitmentManager()
            session_id = f"session_{int(time.time())}"
            commitment = commitment_manager.generate_reception_commitment(
                b"sample_public_key", session_id
            )

            print(f"📝 Your reception commitment: {commitment.hex()[:16]}...")
            print("✅ Ready to receive and verify proofs")

    except Exception as e:
        print(f"❌ Error during verification: {e}")

    print("🔍 Call verification complete.")


def handle_register_command(args: List[str]):
    """Handle the register command."""
    parser = argparse.ArgumentParser(description='Register your CallDNS identity')
    parser.add_argument('--name', '-n', help='Your display name')
    parser.add_argument('--phone', help='Your phone number')
    parser.add_argument('--export', '-e', action='store_true', help='Export public key')

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return

    print("🔐 Registering CallDNS identity...")

    try:
        # Create identity manager
        identity_manager = IdentityManager()

        # Get public key
        public_key = identity_manager.get_public_key()
        public_key_hex = public_key.hex()

        print(f"✅ Identity generated successfully!")
        print(f"📱 Public Key: {public_key_hex[:32]}...")

        if parsed_args.export:
            print(f"\n📄 Full Public Key (for sharing):")
            print(public_key_hex)

        if parsed_args.name:
            print(f"👤 Name: {parsed_args.name}")

        if parsed_args.phone:
            print(f"📞 Phone: {parsed_args.phone}")

        print("\n💡 Tips:")
        print("   - Share your public key with contacts for verified calling")
        print("   - Keep your private key secure (automatically managed)")
        print("   - Use 'calldns call' to make verified calls")

    except Exception as e:
        print(f"❌ Error during registration: {e}")

    print("🔐 Identity registration complete.")


def handle_call_command(args: List[str]):
    """Handle the call command."""
    parser = argparse.ArgumentParser(description='Make a verified call')
    parser.add_argument('number', nargs='?', help='Phone number to call')
    parser.add_argument('--message', '-m', help='Message to include with the call')
    parser.add_argument('--urgent', '-u', action='store_true', help='Mark as urgent')
    parser.add_argument('--public-key', '-pk', help='Recipient public key (hex)')

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return

    if not parsed_args.number:
        print("❌ Error: Phone number is required")
        print("Usage: calldns call <number> [options]")
        return

    print(f"📞 Making verified call to {parsed_args.number}...")

    try:
        # Create caller
        caller = Caller()

        # Prepare call metadata
        metadata = {
            'timestamp': int(time.time()),
            'call_type': 'voice',
            'urgent': parsed_args.urgent,
            'message': parsed_args.message
        }

        # Generate ZK proof
        print("🔐 Generating zero-knowledge proof...")
        proof = caller.generate_call_proof(metadata)

        print("✅ Proof generated successfully!")
        print(f"📱 Proof ID: {proof.get('R', b'').hex()[:16] if isinstance(proof.get('R'), bytes) else 'N/A'}...")

        # In a real implementation, this would be sent to the network
        print("📡 Broadcasting proof to CallDNS network...")

        if parsed_args.public_key:
            print(f"🎯 Targeted to recipient: {parsed_args.public_key[:16]}...")

        if parsed_args.urgent:
            print("🚨 Marked as URGENT")

        if parsed_args.message:
            print(f"💬 Message: {parsed_args.message}")

        print("\n💡 Call recipient can now verify your identity using:")
        print(f"   calldns verify --proof '{json.dumps(proof, default=str)}'")

    except Exception as e:
        print(f"❌ Error during call: {e}")

    print("📞 Verified call initiated.")


def handle_identity_command(args: List[str]):
    """Handle the identity command."""
    parser = argparse.ArgumentParser(description='Manage your CallDNS identity')
    parser.add_argument('action', nargs='?', choices=['show', 'export', 'regenerate'],
                       default='show', help='Action to perform')

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return

    print("🔐 Managing CallDNS identity...")

    try:
        identity_manager = IdentityManager()

        if parsed_args.action == 'show':
            public_key = identity_manager.get_public_key()
            private_key = identity_manager.get_private_key()

            print("📱 Current Identity:")
            print(f"   Public Key:  {public_key.hex()[:32]}...")
            print(f"   Private Key: {'*' * 32}... (hidden)")
            print(f"   Key Length:  {len(public_key)} bytes")

        elif parsed_args.action == 'export':
            public_key = identity_manager.get_public_key()
            print("📄 Exportable Public Key:")
            print(public_key.hex())
            print("\n💡 Share this key with contacts for verified calling")

        elif parsed_args.action == 'regenerate':
            print("⚠️  Regenerating identity will invalidate existing keys!")
            confirm = input("Are you sure? (yes/no): ")
            if confirm.lower() == 'yes':
                identity_manager._generate_identity()
                new_public_key = identity_manager.get_public_key()
                print("✅ New identity generated!")
                print(f"📱 New Public Key: {new_public_key.hex()[:32]}...")
            else:
                print("❌ Identity regeneration cancelled")

    except Exception as e:
        print(f"❌ Error managing identity: {e}")

    print("🔐 Identity management complete.")


def handle_contacts_command(args: List[str]):
    """Handle the contacts command."""
    parser = argparse.ArgumentParser(description='Manage your CallDNS contacts')
    parser.add_argument('action', nargs='?', choices=['list', 'add', 'remove', 'verify'],
                       default='list', help='Action to perform')
    parser.add_argument('--name', '-n', help='Contact name')
    parser.add_argument('--phone', '-p', help='Contact phone number')
    parser.add_argument('--key', '-k', help='Contact public key (hex)')

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return

    print("👥 Managing CallDNS contacts...")

    # Simple in-memory contact storage for demo
    # In production, this would be persistent storage
    contacts = {}

    try:
        if parsed_args.action == 'list':
            if not contacts:
                print("📝 No contacts found")
                print("💡 Use 'calldns contacts add' to add contacts")
            else:
                print("📞 Your Contacts:")
                for name, info in contacts.items():
                    print(f"   👤 {name}")
                    print(f"      📱 {info.get('phone', 'No phone')}")
                    print(f"      🔐 {info.get('key', 'No key')[:16]}...")

        elif parsed_args.action == 'add':
            if not parsed_args.name:
                print("❌ Error: Contact name is required")
                return

            contact_info = {}
            if parsed_args.phone:
                contact_info['phone'] = parsed_args.phone
            if parsed_args.key:
                contact_info['key'] = parsed_args.key

            contacts[parsed_args.name] = contact_info
            print(f"✅ Contact '{parsed_args.name}' added successfully!")

        elif parsed_args.action == 'remove':
            if not parsed_args.name:
                print("❌ Error: Contact name is required")
                return

            if parsed_args.name in contacts:
                del contacts[parsed_args.name]
                print(f"✅ Contact '{parsed_args.name}' removed successfully!")
            else:
                print(f"❌ Contact '{parsed_args.name}' not found")

        elif parsed_args.action == 'verify':
            if not parsed_args.name:
                print("❌ Error: Contact name is required")
                return

            if parsed_args.name not in contacts:
                print(f"❌ Contact '{parsed_args.name}' not found")
                return

            contact = contacts[parsed_args.name]
            if 'key' not in contact:
                print(f"❌ No public key found for '{parsed_args.name}'")
                return

            print(f"🔍 Verifying contact '{parsed_args.name}'...")
            print(f"📱 Public Key: {contact['key'][:32]}...")
            print("✅ Contact verification ready")

    except Exception as e:
        print(f"❌ Error managing contacts: {e}")

    print("👥 Contacts management complete.")


if __name__ == '__main__':
    main()