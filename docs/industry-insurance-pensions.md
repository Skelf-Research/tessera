# CallDNS for Insurance & Pensions

## Regulatory Landscape

Insurance companies and pension providers manage long-term financial relationships with vulnerable customers. Regulators increasingly focus on consumer protection, particularly for retirees and those approaching retirement who are prime targets for impersonation fraud.

### Key Regulations

#### FCA Consumer Duty (UK)
The Consumer Duty requires firms to:
- Act to deliver good outcomes for retail customers
- Take particular care with vulnerable customers
- Ensure communications are clear and not misleading

**How CallDNS helps**: Enables customers to verify legitimate provider calls, protecting vulnerable populations from impersonation fraud.

#### The Pensions Regulator (TPR) Requirements
TPR expects schemes to:
- Communicate effectively with members
- Protect members from scams
- Provide clear information about benefits

**How CallDNS helps**: Members can verify pension scheme communications are legitimate before sharing personal information.

#### Pension Schemes Act 2021
Introduces requirements for:
- Member communications standards
- Scam prevention measures
- Trustee oversight of member interactions

**How CallDNS helps**: Cryptographic verification demonstrates proactive scam prevention measures.

#### Insurance Distribution Directive (IDD)
Requires insurers to:
- Act honestly, fairly, and professionally
- Ensure marketing communications are clear and not misleading
- Document customer interactions

**How CallDNS helps**: Proof generation creates auditable records of legitimate customer communications.

#### GDPR / Data Protection Act 2018
Requires:
- Privacy by design
- Data minimization
- Protection of personal data

**How CallDNS helps**: Zero-knowledge proofs verify identity without transmitting or storing personal data.

#### State Insurance Regulations (US)
Various state departments of insurance require:
- Consumer protection measures
- Fraud prevention programs
- Clear communication standards

**How CallDNS helps**: Demonstrates proactive fraud prevention in regulatory examinations.

---

## The Vulnerability Challenge

### High-Risk Customer Population

Insurance and pension customers are particularly vulnerable to voice fraud:

1. **Retirement savings**: Large accumulated balances attract fraudsters
2. **Age demographics**: Older customers may be more trusting of callers
3. **Complex products**: Legitimate calls often involve complex discussions
4. **Infrequent contact**: Customers may not recognize legitimate caller patterns

### Common Fraud Scenarios

- **Pension liberation scams**: Fraudsters impersonate advisors offering early access to pensions
- **Insurance policy scams**: Fake calls about policy changes or premium refunds
- **Investment fraud**: Impersonating providers to redirect retirement funds
- **Annuity fraud**: Fake calls about annuity rates or surrender values

---

## Implementation Scenarios

### Pension Scheme Communications

#### Member Outreach

```python
from calldns.sdk import Caller

class PensionSchemeOutreach:
    def __init__(self, scheme_name: str, tpr_reference: str):
        self.caller = Caller(identity=f"pension_{tpr_reference}")
        self.scheme_name = scheme_name
        self.tpr_ref = tpr_reference

    def generate_member_call_proof(self, call_purpose: str) -> dict:
        """Generate proof for pension scheme member call."""

        return self.caller.generate_call_proof(
            metadata={
                "scheme_name": self.scheme_name,
                "tpr_reference": self.tpr_ref,
                "call_purpose": call_purpose,
                "vulnerable_customer_protocol": True
            }
        )

# Usage
scheme = PensionSchemeOutreach(
    scheme_name="ABC Company Pension Scheme",
    tpr_reference="12345678"
)

# Proof for retirement planning call
proof = scheme.generate_member_call_proof("retirement_options_discussion")

# Member verifies via scheme portal:
# "Verified: ABC Company Pension Scheme called about your retirement options"
```

#### Member Portal Verification

```javascript
// React component for pension member portal
function VerifySchemeCall({ memberId }) {
  const [recentCalls, setRecentCalls] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    callDNS.getRecentProofs({ hours: 72 })
      .then(proofs => {
        setRecentCalls(proofs.filter(p =>
          p.metadata.tpr_reference // Only pension-related proofs
        ));
        setLoading(false);
      });
  }, [memberId]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="call-verification-section">
      <h2>Verify Recent Calls</h2>
      <p className="warning-text">
        Your pension scheme will never ask for your full password, PIN, or
        request immediate fund transfers. If in doubt, hang up and call us
        using the number on your statement.
      </p>

      {recentCalls.length === 0 ? (
        <p>No verified calls from your pension scheme in the last 72 hours.</p>
      ) : (
        <div className="calls-list">
          {recentCalls.map(call => (
            <div key={call.id} className="verified-call-card">
              <div className="verified-badge">✓ Verified Call</div>
              <h3>{call.metadata.scheme_name}</h3>
              <p><strong>Purpose:</strong> {formatPurpose(call.metadata.call_purpose)}</p>
              <p><strong>Time:</strong> {formatDateTime(call.timestamp)}</p>
              <p className="tpr-ref">TPR Ref: {call.metadata.tpr_reference}</p>
            </div>
          ))}
        </div>
      )}

      <div className="fraud-warning">
        <h3>Received a call not shown here?</h3>
        <p>
          If you received a call claiming to be from your pension scheme that
          doesn't appear in this list, it may be fraudulent. Please contact us
          immediately.
        </p>
        <button onClick={() => window.location.href = '/report-fraud'}>
          Report Suspicious Call
        </button>
      </div>
    </div>
  );
}
```

---

### Insurance Provider Communications

#### Policy Service Calls

```python
from calldns.sdk import Caller

class InsuranceOutreach:
    def __init__(self, company_name: str, fca_reference: str):
        self.caller = Caller(identity=f"insurer_{fca_reference}")
        self.company = company_name
        self.fca_ref = fca_reference

    def generate_policy_call_proof(self, call_type: str, policy_type: str) -> dict:
        """Generate proof for insurance policy call."""

        return self.caller.generate_call_proof(
            metadata={
                "company": self.company,
                "fca_reference": self.fca_ref,
                "call_type": call_type,  # "renewal", "claim_update", "policy_change"
                "policy_type": policy_type,  # "life", "motor", "home", "health"
                "idd_compliant": True
            }
        )

# Usage
insurer = InsuranceOutreach(
    company_name="Secure Life Insurance",
    fca_reference="123456"
)

proof = insurer.generate_policy_call_proof(
    call_type="renewal",
    policy_type="life"
)
```

#### Mobile App Verification

```kotlin
// Android - Insurance customer app
@Composable
fun VerifyInsurerCall(
    customerId: String,
    incomingCallerId: String
) {
    var verification by remember { mutableStateOf<VerificationResult?>(null) }

    LaunchedEffect(incomingCallerId) {
        verification = CallDNS.verify(
            CallContext(
                callerId = incomingCallerId,
                metadata = mapOf("customer_id" to customerId)
            )
        )
    }

    Card(
        modifier = Modifier.fillMaxWidth().padding(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            when (val result = verification) {
                is VerificationResult.Verified -> {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Default.VerifiedUser,
                            contentDescription = "Verified",
                            tint = Color.Green,
                            modifier = Modifier.size(32.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column {
                            Text(
                                "Verified Call",
                                style = MaterialTheme.typography.h6
                            )
                            Text(
                                result.metadata["company"] ?: "",
                                style = MaterialTheme.typography.body1
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        "Call type: ${result.metadata["call_type"]}",
                        style = MaterialTheme.typography.body2
                    )
                    Text(
                        "FCA Reference: ${result.metadata["fca_reference"]}",
                        style = MaterialTheme.typography.caption,
                        color = Color.Gray
                    )
                }

                is VerificationResult.Unverified -> {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = "Warning",
                            tint = Color.Red,
                            modifier = Modifier.size(32.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "Unverified Caller",
                            style = MaterialTheme.typography.h6,
                            color = Color.Red
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        "This call could not be verified. Do not share policy " +
                        "details or personal information until you verify the " +
                        "caller through official channels.",
                        style = MaterialTheme.typography.body2
                    )

                    Button(
                        onClick = { /* Navigate to fraud reporting */ },
                        modifier = Modifier.padding(top = 8.dp)
                    ) {
                        Text("Report Suspicious Call")
                    }
                }

                null -> CircularProgressIndicator()
            }
        }
    }
}
```

---

### Annuity and Retirement Income

#### Annuity Provider Communications

```python
from calldns.sdk import Caller

class AnnuityProvider:
    def __init__(self, provider_name: str, fca_ref: str):
        self.caller = Caller(identity=f"annuity_{fca_ref}")
        self.provider = provider_name

    def generate_annuity_call_proof(self, call_purpose: str) -> dict:
        """Generate proof for annuity-related call."""

        return self.caller.generate_call_proof(
            metadata={
                "provider": self.provider,
                "product_type": "annuity",
                "call_purpose": call_purpose,  # "quote", "payment_query", "death_benefit"
                "vulnerable_customer_protocol": True,
                "scam_prevention_enabled": True
            }
        )

# Usage - critical for preventing pension liberation fraud
provider = AnnuityProvider(
    provider_name="Retirement Income Co",
    fca_ref="789012"
)

proof = provider.generate_annuity_call_proof("retirement_options")
```

---

### Vulnerable Customer Protocol

#### Enhanced Verification for Vulnerable Customers

```python
from calldns.sdk import Caller

class VulnerableCustomerOutreach:
    def __init__(self, company_name: str, fca_ref: str):
        self.caller = Caller(identity=f"company_{fca_ref}")
        self.company = company_name

    def generate_vulnerable_customer_proof(
        self,
        call_purpose: str,
        additional_protections: list
    ) -> dict:
        """Generate enhanced proof with vulnerable customer protections."""

        return self.caller.generate_call_proof(
            metadata={
                "company": self.company,
                "call_purpose": call_purpose,
                "vulnerable_customer_protocol": True,
                "additional_protections": additional_protections,
                "consumer_duty_compliant": True
            }
        )

# Usage
outreach = VulnerableCustomerOutreach(
    company_name="Pension Trustees Ltd",
    fca_ref="345678"
)

proof = outreach.generate_vulnerable_customer_proof(
    call_purpose="retirement_planning",
    additional_protections=[
        "callback_offered",
        "written_confirmation_provided",
        "cooling_off_period_explained",
        "independent_advice_suggested"
    ]
)
```

#### Customer-Facing Verification UI

```swift
// iOS SwiftUI - Pension/Insurance app
struct VulnerableCustomerVerification: View {
    let callerId: String
    @State private var verification: VerificationResult?

    var body: some View {
        VStack(spacing: 20) {
            // Verification result
            if let result = verification {
                if result.isVerified {
                    VStack(spacing: 12) {
                        Image(systemName: "checkmark.shield.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.green)

                        Text("Verified Call")
                            .font(.title2)
                            .fontWeight(.bold)

                        Text(result.metadata["company"] ?? "Your Provider")
                            .font(.headline)

                        // Show additional protections
                        if let protections = result.metadata["additional_protections"] as? [String] {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Your Protections:")
                                    .font(.subheadline)
                                    .fontWeight(.semibold)

                                ForEach(protections, id: \.self) { protection in
                                    HStack {
                                        Image(systemName: "checkmark.circle.fill")
                                            .foregroundColor(.green)
                                            .font(.caption)
                                        Text(formatProtection(protection))
                                            .font(.caption)
                                    }
                                }
                            }
                            .padding()
                            .background(Color.green.opacity(0.1))
                            .cornerRadius(8)
                        }
                    }
                } else {
                    VStack(spacing: 12) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.red)

                        Text("Unverified Caller")
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundColor(.red)

                        Text("This caller could not be verified.")
                            .font(.body)

                        VStack(alignment: .leading, spacing: 8) {
                            Text("Protect Yourself:")
                                .font(.subheadline)
                                .fontWeight(.semibold)

                            BulletPoint("Do not share personal details")
                            BulletPoint("Do not agree to transfer money")
                            BulletPoint("Hang up and call us using the number on your statement")
                            BulletPoint("Report this call to us immediately")
                        }
                        .padding()
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(8)
                    }
                }
            } else {
                ProgressView("Verifying caller...")
            }
        }
        .padding()
        .onAppear {
            Task {
                verification = await CallDNS.verify(callerId: callerId)
            }
        }
    }

    private func formatProtection(_ protection: String) -> String {
        // Convert snake_case to readable text
        protection.replacingOccurrences(of: "_", with: " ").capitalized
    }
}
```

---

## Compliance Reporting

### TPR and FCA Reporting

```python
from calldns.logging import ComplianceLogger

class PensionInsuranceCompliance:
    def __init__(self):
        self.logger = ComplianceLogger()

    def generate_consumer_duty_report(self, date_range: tuple) -> dict:
        """Generate FCA Consumer Duty compliance report."""

        verifications = self.logger.get_verifications(date_range)

        return {
            "period": date_range,
            "consumer_duty_compliance": {
                "customer_outcome_focus": True,
                "vulnerable_customer_protection": True,
                "scam_prevention_measures": True
            },
            "verification_metrics": {
                "total_outbound_calls": len(verifications),
                "verification_enabled": len([v for v in verifications if v.get("verified")]),
                "vulnerable_customer_calls": len([
                    v for v in verifications
                    if v.get("metadata", {}).get("vulnerable_customer_protocol")
                ])
            },
            "fraud_prevention": {
                "verification_lookups": self.logger.get_verification_requests(date_range),
                "fraud_reports_received": self.logger.get_fraud_reports(date_range)
            }
        }

    def generate_tpr_report(self, scheme_id: str, date_range: tuple) -> dict:
        """Generate TPR compliance report for pension scheme."""

        verifications = self.logger.get_scheme_verifications(scheme_id, date_range)

        return {
            "scheme_id": scheme_id,
            "period": date_range,
            "member_communications": {
                "total_calls": len(verifications),
                "verification_enabled": True,
                "scam_prevention_active": True
            },
            "trustee_oversight": {
                "verification_system_in_place": True,
                "member_portal_access": True,
                "fraud_reporting_mechanism": True
            }
        }
```

---

## Integration Architecture

### Pension Administration System Integration

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Pension Admin  │────▶│   CallDNS    │────▶│  Member Portal  │
│  System         │     │   Service    │     │                 │
│                 │     │              │     │  - Verify calls │
│  - Generate     │     │  - Proof     │     │  - Report fraud │
│    proof before │     │    storage   │     │  - View history │
│    member call  │     │  - Audit log │     │                 │
└─────────────────┘     └──────────────┘     └─────────────────┘
         │                      │
         │                      │
         ▼                      ▼
┌─────────────────┐     ┌──────────────┐
│  Scheme         │     │  TPR / FCA   │
│  Trustees       │     │  Reporting   │
└─────────────────┘     └──────────────┘
```

---

## ROI Considerations

### Fraud Prevention
- Average pension scam loss: £50,000+ per victim
- Insurance fraud prevention reduces claims leakage
- Demonstrates proactive scam prevention to regulators

### Regulatory Compliance
- Avoid FCA fines (up to £50M+ for serious breaches)
- Demonstrate Consumer Duty compliance
- Meet TPR expectations for member protection
- Streamlined regulatory examinations

### Customer Trust
- Reduces member anxiety about scam calls
- Lower call screening/abandonment
- Improved customer satisfaction scores
- Enhanced brand reputation

### Operational Efficiency
- Faster member callbacks
- Reduced verification overhead
- Lower fraud investigation costs
- Streamlined vulnerable customer processes

---

## Getting Started

### Pilot Program

1. **Select pilot scope**: Start with retirement planning calls or annuity queries
2. **Integration**: Connect to pension admin system and member portal
3. **Staff training**: Train call handlers on proof generation and vulnerable customer protocol
4. **Member education**: Inform members about verification feature via annual statements
5. **Monitor**: Track verification rates, fraud reports, member feedback

### Trustee Considerations

For pension schemes, trustees should:
- Review CallDNS as part of scam prevention measures
- Include in scheme governance reporting
- Consider for cybersecurity risk assessment
- Document as evidence of member protection efforts

### Contact

For pension and insurance deployment support, contact your CallDNS representative.

---

*CallDNS helps insurance and pension providers protect vulnerable customers while meeting Consumer Duty and TPR requirements.*
