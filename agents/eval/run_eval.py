import os
import json
import importlib

from agent import TextDAggerAgent
import modules.generic as generic
import eval.evaluate as evaluate
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def run_eval():
    config = generic.load_config()
    agent = TextDAggerAgent(config)

    output_dir = config["general"]["save_path"]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # load model from checkpoint
    data_dir = config["general"]["save_path"]
    if agent.load_pretrained:
        if os.path.exists(data_dir + "/" + agent.load_from_tag + ".pt"):
            agent.load_pretrained_model(data_dir + "/" + agent.load_from_tag + ".pt")
            agent.update_target_net()

    # iterate through eval directories
    training_method = config["general"]["training_method"]
    eval_paths = config["general"]["evaluate"]["eval_paths"]
    eval_envs = config["general"]["evaluate"]["envs"]
    controllers = config["general"]["evaluate"]["controllers"]
    repeats = config["general"]["evaluate"]["repeats"]
    for eval_env_type in eval_envs:
        for controller_type in (controllers if eval_env_type == "AlfredThorEnv" else ["tw"]):
            print("Setting controller: %s" % controller_type)
            for eval_path in eval_paths:
                print("Evaluating: %s" % eval_path)
                config["general"]["evaluate"]["env"]["type"] = eval_env_type
                config["dataset"]["eval_ood_data_path"] = eval_path
                config["controller"]["type"] = controller_type

                alfred_env = getattr(importlib.import_module("environment"), config["general"]["evaluate"]["env"]["type"])(config, train_eval="eval_out_of_distribution")
                eval_env = alfred_env.init_env(batch_size=agent.eval_batch_size)

                # evaluate
                if training_method == "dagger":
                    results = evaluate.evaluate_dagger(eval_env, agent, alfred_env.num_games*repeats)
                elif training_method == "dqn":
                    results = evaluate.evaluate_dqn(eval_env, agent, alfred_env.num_games*repeats)
                else:
                    raise NotImplementedError()

                split_name = eval_path.split("/")[-1]
                experiment_name = config["general"]["evaluate"]["eval_experiment_tag"]
                results_json = os.path.join(output_dir, "{}_{}_{}_{}.json".format(experiment_name, eval_env_type.lower(), controller_type, split_name))

                with open(results_json, 'w') as f:
                    json.dump(results, f, indent=4, sort_keys=True)
                print("Saved %s" % results_json)

                eval_env.close()


if __name__ == '__main__':
    run_eval()
