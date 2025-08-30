export const metadata = {
  title: 'Penalty Case Search',
  description: 'Search penalty cases from MongoDB',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif', margin: 0 }}>
        {children}
      </body>
    </html>
  );
}

