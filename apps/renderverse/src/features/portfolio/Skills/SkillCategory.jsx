import styles from "./Skills.module.css";
import SkillCategoryItem from "./SkillCategoryItem";
import PropTypes from "prop-types";

const SkillCategory = ({ category, contents }) => {
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

SkillCategory.propTypes = {
  category: PropTypes.string,
  contents: PropTypes.array,
};

export default SkillCategory;
