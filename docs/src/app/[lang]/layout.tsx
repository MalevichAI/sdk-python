import { RootProvider } from 'fumadocs-ui/provider/next';
import { defineI18nUI } from 'fumadocs-ui/i18n';
import { i18n } from '@/lib/i18n';
import '../global.css';
import { Inter } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
});

const { provider } = defineI18nUI(i18n, {
  translations: {
    en: {
      displayName: 'English',
      search: 'Search',
      searchNoResult: 'No results found',
      toc: 'On This Page',
      lastUpdate: 'Last updated on',
      chooseTheme: 'Choose theme',
      nextPage: 'Next',
      previousPage: 'Previous',
    },
    ru: {
      displayName: 'Русский',
      search: 'Поиск',
      searchNoResult: 'Результаты не найдены',
      toc: 'На этой странице',
      lastUpdate: 'Последнее обновление',
      chooseTheme: 'Выбрать тему',
      nextPage: 'Следующая',
      previousPage: 'Предыдущая',
    },
  },
});

export default async function RootLayout({
  params,
  children,
}: {
  params: Promise<{ lang: string }>;
  children: React.ReactNode;
}) {
  const lang = (await params).lang;

  return (
    <html lang={lang} className={inter.className} suppressHydrationWarning>
      <body className="flex flex-col min-h-screen">
        <RootProvider i18n={provider(lang)}>{children}</RootProvider>
      </body>
    </html>
  );
}

