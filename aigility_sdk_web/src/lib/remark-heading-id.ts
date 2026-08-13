import { visit } from 'unist-util-visit';
import type { Root } from 'mdast';

/**
 * Remark plugin that extracts {#id} from heading text and sets it as the
 * heading's HTML id attribute.
 *
 * Transforms:
 *   ## 1. SDK 概述 {#overview}
 * into:
 *   <h2 id="overview">1. SDK 概述</h2>
 */
export default function remarkHeadingId() {
  return (tree: Root) => {
    visit(tree, 'heading', (node) => {
      const lastChild = node.children[node.children.length - 1];
      if (lastChild && lastChild.type === 'text') {
        const match = lastChild.value.match(/\s*\{#([^}]+)\}\s*$/);
        if (match) {
          // Remove the {#id} suffix from the heading text
          lastChild.value = lastChild.value.replace(/\s*\{#([^}]+)\}\s*$/, '');
          // Set the id on the heading node's HTML properties
          node.data = node.data || {};
          node.data.hProperties = { ...(node.data.hProperties || {}), id: match[1] };
        }
      }
    });
  };
}
