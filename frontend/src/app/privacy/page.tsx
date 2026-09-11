import Link from "next/link";
import { LegalPage } from "@/components/legal/LegalPage";

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      summary={<p>LedgerPilot AI is a development and human-review prototype. The public repository and demo are designed for synthetic data only. Do not upload real invoices, receipts, client records, bank details, taxpayer identifiers, employee data, or other real personal or confidential financial information.</p>}
      sections={[
        {
          title: "Data minimisation and purpose",
          body: <p>The application should process only information needed for the demonstrated accounting workflow, authorised testing, security, and support. Development fixtures, examples, screenshots, and demo uploads must remain synthetic.</p>,
        },
        {
          title: "Document intake",
          body: <p>The intake workflow accepts PDF/JPG/PNG files for extraction and review. In this public development context, those files must be synthetic. A production deployment handling real client documents would require an approved privacy notice, lawful processing basis, retention schedule, access controls, processor agreements, cross-border review, breach procedures, and secure deletion rules before use.</p>,
        },
        {
          title: "Accounts, tenants and access",
          body: <p>The architecture includes firm/client and role context. Tenant separation and least-privilege access are privacy requirements, not merely convenience features. A production environment must validate those controls independently before real data is introduced.</p>,
        },
        {
          title: "Logs and diagnostics",
          body: <p>Logs should contain safe identifiers and operational metadata only. They should not copy full documents, raw OCR text, corrected values, credentials, bank details, taxpayer identifiers, or unnecessary personal information.</p>,
        },
        {
          title: "Analytics and advertising",
          body: <p>The audited frontend does not include Google Analytics, Meta Pixel, Hotjar, Mixpanel, PostHog, or similar behavioural advertising analytics. If non-essential tracking is introduced, this policy and consent controls must be reviewed before it is enabled.</p>,
        },
        {
          title: "Third-party processing",
          body: <p>A production deployment may rely on hosting, extraction/AI, authentication, storage, observability, or integration providers. Their exact roles, locations, contracts, and transfer safeguards must be documented for the deployed environment before processing real client data.</p>,
        },
        {
          title: "Malaysia and privacy rights",
          body: <p>LedgerPilot is developed in Malaysia. Production handling of real personal data requires an independent assessment of the Personal Data Protection Act 2010 and other applicable accounting, tax, employment, confidentiality, and professional obligations. Questions about the project can be raised through the repository linked from the <Link href="/">application</Link>.</p>,
        },
      ]}
    />
  );
}
