declare module "pagedjs" {
  export class Previewer {
    preview(
      content: string,
      stylesheets: Record<string, string>[],
      renderTo: HTMLElement,
    ): Promise<{ total: number }>;
  }
}
