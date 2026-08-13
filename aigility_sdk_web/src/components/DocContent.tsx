import { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkHeadingId from '@/lib/remark-heading-id';
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import bash from 'highlight.js/lib/languages/bash';
import json from 'highlight.js/lib/languages/json';
import { Check, Copy } from 'lucide-react';
import { cn } from '@/lib/utils';
import 'highlight.js/styles/github-dark.css';
import { UniversalLink } from '@lark-apaas/client-toolkit-lite';

// Register languages
hljs.registerLanguage('python', python);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('shell', bash);
hljs.registerLanguage('json', json);
hljs.registerLanguage('console', bash);

interface CodeBlockProps {
  code: string;
  language?: string;
}

function CodeBlock({ code, language = 'text' }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const highlighted = useMemo(() => {
    try {
      if (language && hljs.getLanguage(language)) {
        return hljs.highlight(code, { language }).value;
      }
      return hljs.highlightAuto(code).value;
    } catch {
      return code.replace(/&/g, '&amp;').replace(/</g, '&lt;');
    }
  }, [code, language]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const lines = highlighted.split('\n');
  const rawLines = code.split('\n');
  // Remove trailing empty line
  const displayLines = rawLines[rawLines.length - 1] === '' ? lines.slice(0, -1) : lines;

  return (
    <div className="group relative my-4 overflow-hidden rounded-lg border border-border/40 bg-[#0d1117]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 bg-white/[0.02] px-3 py-1.5">
        <span className="text-xs font-medium text-gray-400">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className={cn(
            'flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors',
            'text-gray-400 hover:bg-white/10 hover:text-white',
          )}
          aria-label="复制代码"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" />
              <span>已复制</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>复制</span>
            </>
          )}
        </button>
      </div>

      {/* Code */}
      <div className="flex overflow-x-auto">
        {/* Line numbers */}
        <pre className="select-none border-r border-white/5 bg-black/20 px-3 py-3 text-right text-xs text-gray-500 font-mono leading-6">
          {displayLines.map((_, i) => (
            <div key={i} className="tabular-nums">
              {i + 1}
            </div>
          ))}
        </pre>

        {/* Code content */}
        <pre className="flex-1 px-4 py-3 text-sm font-mono leading-6 overflow-x-auto text-gray-100">
          <code
            className="hljs block"
            dangerouslySetInnerHTML={{ __html: displayLines.join('\n') }}
          />
        </pre>
      </div>
    </div>
  );
}

interface DocContentProps {
  content: string;
}

export default function DocContent({ content }: DocContentProps) {
  return (
    <article className="max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkHeadingId]}
        components={{
          h1: ({ id, children }) => (
            <h1
              id={id}
              className="text-3xl font-bold text-foreground mt-2 mb-6 pb-4 border-b border-border/60"
            >
              {children}
            </h1>
          ),
          h2: ({ id, children }) => (
            <h2
              id={id}
              className="text-2xl font-bold text-foreground mt-10 mb-4 scroll-mt-20 group"
            >
              <UniversalLink
                to={`#${id}`}
                className="opacity-0 group-hover:opacity-100 mr-2 text-muted-foreground transition-opacity text-base font-normal"
                aria-label="锚点链接"
              >
                #
              </UniversalLink>
              {children}
            </h2>
          ),
          h3: ({ id, children }) => (
            <h3
              id={id}
              className="text-xl font-semibold text-foreground mt-6 mb-3 scroll-mt-20 group"
            >
              <UniversalLink
                to={`#${id}`}
                className="opacity-0 group-hover:opacity-100 mr-2 text-muted-foreground transition-opacity text-sm font-normal"
                aria-label="锚点链接"
              >
                #
              </UniversalLink>
              {children}
            </h3>
          ),
          h4: ({ id, children }) => (
            <h4
              id={id}
              className="text-base font-semibold text-foreground mt-5 mb-2 scroll-mt-20"
            >
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="text-foreground/85 leading-7 my-4">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="my-4 ml-6 list-disc space-y-1.5 text-foreground/85">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-4 ml-6 list-decimal space-y-1.5 text-foreground/85">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-7">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-4 border-l-4 border-primary/40 bg-primary/5 px-4 py-3 text-foreground/85 rounded-r-md">
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => {
            const isExternal = href?.startsWith('http');
            if (isExternal) {
              return (
                <UniversalLink
                  to={href}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary underline-offset-2 hover:underline"
                >
                  {children}
                </UniversalLink>
              );
            }
            return (
              <UniversalLink to={href} className="text-primary underline-offset-2 hover:underline">
                {children}
              </UniversalLink>
            );
          },
          table: ({ children }) => (
            <div className="my-4 w-full overflow-x-auto rounded-md border border-border/60">
              <table className="w-full border-collapse text-sm">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/50">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="border-b border-border/60 px-4 py-2.5 text-left font-semibold text-foreground">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-t border-border/40 px-4 py-2.5 text-foreground/85">
              {children}
            </td>
          ),
          hr: () => <hr className="my-8 border-border/40" />,
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          code: ({ className, children }) => {
            const match = /language-(\w+)/.exec(className || '');
            if (!match) {
              return (
                <code className="relative rounded bg-muted px-1.5 py-0.5 font-mono text-sm text-foreground/90 border border-border/50">
                  {children}
                </code>
              );
            }
            return null;
          },
          pre: ({ children, className }) => {
            // Extract code element's content and language
            const codeEl = Array.isArray(children) ? children[0] : children;
            const codeElAny = codeEl as { props?: { children?: string; className?: string } };
            const rawCode = String(codeElAny?.props?.children ?? '');
            const langMatch = /language-(\w+)/.exec(codeElAny?.props?.className || '');
            const lang = langMatch ? langMatch[1] : 'text';

            return <CodeBlock code={rawCode} language={lang} />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </article>
  );
}
