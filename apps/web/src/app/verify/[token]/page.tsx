import { CertificateVerification } from "../../../components/certificate";
import { isLang } from "../../../lib/i18n/keys";

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ token: string }>;
  searchParams: Promise<{ lang?: string | string[] }>;
}) {
  const [{ token }, { lang }] = await Promise.all([params, searchParams]);
  return <CertificateVerification token={token} lang={isLang(lang) ? lang : undefined} />;
}
