import styles from "./Skills.module.css";
import SkillCategoryItem from "./SkillCategoryItem";
import type { SkillItem } from "@/features/portfolio/types";

interface SkillCategoryProps {
  category: string;
  contents: SkillItem[];
}

const SkillCategory = ({ category, contents }: SkillCategoryProps) => {
  return (
    <section className={styles.category}>
      <h6 className={styles.heading}>{category}</h6>
      <ul className={styles.items}>
        {contents.map((item) => (
          <SkillCategoryItem item={item} key={item.name} />
        ))}
      </ul>
    </section>
  );
};

export default SkillCategory;
