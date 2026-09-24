import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "يوم أول | شغلك يبدأ من هنا",
  description:
    "تجربة شغل حقيقية، خطوة بخطوة. اتدرّب على المهارات الرقمية من خلال مهام عملية.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ar" dir="rtl">
      <body>
        <a className="skip" href="#main">
          انتقل للمحتوى
        </a>
        {children}
      </body>
    </html>
  );
}
