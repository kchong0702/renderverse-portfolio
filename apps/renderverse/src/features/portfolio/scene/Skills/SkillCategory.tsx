import styles from "./Skills.module.css";

interface SkillCategoryProps {
  category: string;
  contents: string[];
}

const SkillCategory = ({ category, contents }: SkillCategoryProps) => {
  return (
    <section className={styles.category}>
      <h6 className={styles.heading}>{category}</h6>
      <ul className={styles.items}>
        {contents.map((name) => (
          <li className={styles.item} key={name}>
            {name}
          </li>
        ))}
      </ul>
    </section>
  );
};

export default SkillCategory;
