import { useTranslation } from "react-i18next";
import { newId, valueOf } from "../../lib/items";
import { useEditorStore } from "../../state/editorStore";
import { dashedPillClass, unzoom } from "./chrome";
import { usePage } from "./PageContext";

export default function AddSkill({
  parent,
  after,
}: {
  parent: string;
  after: string | null;
}) {
  const { t } = useTranslation();
  const page = usePage();
  const block = parent.split("/")[1];
  const hot = useEditorStore(
    (state) => state.hovered.block === block || state.selected === `k:${block}`,
  );
  const { focusNext } = useEditorStore.getState();

  if (!hot) return null;
  return (
    <button
      type="button"
      onClick={() => {
        const item = { id: newId(), text: valueOf("", page.source) };
        focusNext(`${parent}/${item.id}/text`);
        page.edit([{ kind: "insert_item", parent, after, item }]);
      }}
      className={`${dashedPillClass} ${unzoom} absolute z-[4] ml-1.5 h-5 px-2 [ul>&]:static [ul>&]:ml-0 [ul>&]:self-center`}
    >
      {t("documents.page.skill")}
    </button>
  );
}
