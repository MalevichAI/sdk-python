import Link from 'next/link';

export default async function HomePage(props: PageProps<'/[lang]'>) {
  const params = await props.params;
  const lang = params.lang;

  const content = {
    en: {
      title: 'Malevich SDK',
      subtitle: 'Build powerful data processing pipelines',
      docsLink: 'Documentation',
    },
    ru: {
      title: 'Malevich SDK',
      subtitle: 'Создавайте мощные конвейеры обработки данных',
      docsLink: 'Документация',
    },
  };

  const text = content[lang as keyof typeof content] || content.en;

  return (
    <div className="flex flex-col justify-center text-center flex-1">
      <h1 className="text-4xl font-bold mb-4">{text.title}</h1>
      <p className="text-xl text-muted-foreground mb-8">{text.subtitle}</p>
      <div>
        <Link
          href={`/${lang}/docs`}
          className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
        >
          {text.docsLink}
        </Link>
      </div>
    </div>
  );
}
