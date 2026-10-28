import styles from "./Skills.module.css";
import Rating from "./Rating";
import type { SkillItem } from "@/features/portfolio/types";

const SkillCategoryItem = ({ item }: { item: SkillItem }) => {
  const { name, rating } = item;
  return (
    <li className={styles.item}>
      {name}
      <Rating size="0.6em" checked={rating} />
    </li>
  );
};

export default SkillCategoryItem;
