import { HomeLayout } from 'fumadocs-ui/layouts/home';
import { baseOptions } from '@/lib/layout.shared';

export default async function Layout({
  params,
  children,
}: LayoutProps<'/[lang]'>) {
  const lang = (await params).lang;

  return <HomeLayout {...baseOptions(lang)}>{children}</HomeLayout>;
}
