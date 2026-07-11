import './globals.css';

export const metadata = {
  title: 'Hataken Othellonia',
  description: 'Quiz-powered Othello game',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
