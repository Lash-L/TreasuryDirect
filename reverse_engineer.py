"""
This was a side project and you should not expect this logic to work 100%.
It would be a good starting point for a full, well-engineered MITM reverse engineering agent.
"""
import json
import os
from pathlib import Path

from google.genai import types
from mitmproxy.io import FlowReader
from mitmproxy import dns
from mitmproxy import http
from google import genai
import urllib.parse


class MitmAgent:
    def __init__(
        self,
        goal: str,
        existing_information: dict,
        gemini_api_key: str,
        markdown_folder: str = "markdown",
        ignore_existing: bool = False,
    ):
        """
        Create a new MitmAgent instance to help with reverse engineering.
        :param goal: The goal you want to be able to accomplish via the undocumented API.
        :param existing_information: Any information you have as the user that would be helpful for searching the flows.
        :param gemini_api_key: The api key for AI Studio (you can use the free one)
        :param markdown_folder: The folder you want the markdowns to be saved in
        :param ignore_existing: If this agent should ignore the existing markdowns in the markdown folder.
        """
        self._goal = goal
        self._existing_information = existing_information
        self._flow_data = []
        self._client = genai.Client(api_key=gemini_api_key)
        self._markdowns = {}
        self._markdown_folder = markdown_folder
        if not ignore_existing:
            path = Path(markdown_folder)
            os.makedirs(markdown_folder, exist_ok=True)
            for file_path in path.iterdir():
                if file_path.is_file():
                    self._markdowns[file_path.name] = file_path.read_text()

    def parse_flow_file(self, file_path: str) -> None:
        """
        Parse the flow file to find all of the flows that could contain relevant information.
        :param file_path: Path to the flow file.
        """
        with open(file_path, "rb") as flow_file:
            reader = FlowReader(flow_file)
            print(f"Successfully opened flow file: {file_path}\n")

            for flow in reader.stream():
                if isinstance(flow, dns.DNSFlow):
                    print(f"DNS Request: {flow.request.content.decode('utf-8')}")
                elif isinstance(flow, http.HTTPFlow):
                    file_extension = flow.request.path.split(".")[-1]
                    if file_extension in {
                        "css",
                        "png",
                        "jpeg",
                        "jpg",
                        "woff2",
                        "svg",
                        "gif",
                        "ico",
                        "js",
                    }:
                        continue
                    print(f"HTTP Request: {flow.request.pretty_url}")
                    state = flow.get_state()
                    self._flow_data.append(
                        {
                            "id": state["id"],
                            "request": state["request"],
                            "response": state["response"],
                        }
                    )
                else:
                    print(f"Skipping unsupported flow type: {type(flow)}")

    def find_string(self, search_str: str) -> list[dict]:
        """
        Find a string in any of the provided flows.
        :param search_str: The string you want to look for
        :return: A list of all flows that contain this string.
        """
        print(f"Finding string: {search_str}")
        results = []
        for flow in self._flow_data:
            match = (str(flow["response"]) + str(flow["request"])).find(
                urllib.parse.quote_plus(search_str)
            )
            if match != -1:
                results.append(
                    {
                        "id": flow["id"],
                        "request": str(flow["request"]),
                        "response": str(flow["response"]),
                    }
                )
        return results

    def create_documentation(self, flow_json: dict, extra_information: dict) -> str:
        """
        Create documentation for a specific flow.
        :param flow_json: The flow you want to document.
        :param extra_information: Any extra information that is relevant to the documentation.
        :return: The documentation (It is also saved in markdown_folder/flow_id.md)
        """
        print(f"Creating documentation for the following flow: {flow_json['id']}")
        prompt = f"""
        You are a technical writer specializing in API documentation. Your task is to create a clear and concise markdown documentation page for a given REST API request.
    
    
        The user provided the following example data: {json.dumps(extra_information, indent=2)}
    
        The captured API request and response data from MITM is as follows:
        {flow_json}
    
        Based on all this information, create a markdown document that explains how to make this API call.
        The documentation should include:
        - A title for the API call (e.g., "User Login").
        - The HTTP Method and URL.
        - A description of any required Headers.
        - A description and example of the Request Body (if any).
        - A description and example of the Response Body.
        - Make it clear what is required and what the response looks like.
    
        ONLY return valid markdown. Do not include any extra commentary, greetings, or explanations outside of the markdown document itself.
        Return it WITHOUT the markdown formatting tag on the beginning and the end.
        Replace any potentially PII(such as username, password, session numbers, cookies, jwts, etc.) with dummy data.
        """
        markdown = self._client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17", contents=[prompt]
        )
        file_name = f"{flow_json['id']}.md"
        with open(f"{self._markdown_folder}/{file_name}", "w") as f:
            f.write(markdown.text)
        self._markdowns[file_name] = markdown.text
        return markdown.text

    def update_documentation(self, markdown_path: str, extra_information: str) -> str:
        """
        Update existing documentation with extra information.
        :param markdown_path: The path to the markdown file within the markdown folder.
        :param extra_information: The extra information that is relevant to the documentation.
        :return: The new markdown file (It is also saved in markdown_folder/flow_id.md)
        """
        print(f"Updating {markdown_path} with the following info: {extra_information}")
        prompt = f"""
        You are a technical writer specializing in API documentation. Your task is to update an existing markdown documentation page for a given REST API request.
    
        The user provided the following extra data: {extra_information}
    
        ONLY return valid markdown. Do not include any extra commentary, greetings, or explanations outside of the markdown document itself.
        Return it WITHOUT the markdown formatting tag on the beginning and the end.
        Replace any potentially sensitive information with dummy data.
        The current file is:
        f{self._markdowns[markdown_path]}
"""
        markdown = self._client.models.generate_content(
            model="gemini-2.5-flash-lite-preview-06-17", contents=[prompt]
        )
        with open(f"{self._markdown_folder}/{markdown_path}", "w") as f:
            f.write(markdown.text)
        self._markdowns[markdown_path] = markdown.text
        return markdown.text

    def solve(self) -> None:
        """
        Entry point for the agent.
        """
        # In a real system this prompt should be dynamically updating so that markdowns are updating and we could
        # likely reduce the history context.
        prompt = f"""
        You are an expert reverse engineer helping a user make sense of a private API.
        Your goal is to figure out how to achieve a user's goal given flows(data dumps) from MITM. 
        The data represents a specific runthrough and just because a value exists - does not mean that it is always going to be exactly that
        for example if there is a 'uuid' attribute - that likely needs to be created (or found in a earlier api call) every time.
        You currently have the following documentation to help you solve the user's problem: {self._markdowns if self._markdowns else "No documentation available."}
        If the documentation fully solves the user's problem and all relevant information exists - you can likely skip all the future steps.
        You should solve the problem by completing the following steps:
        1) For each attribute that the user provided - determine if they are relevant to the goal at hand.
        2) You can use the 'find_string' tool to find any instances of a string in any flow. So for each attribute that 
        you found relevant, call find_string to get the REST requests that contain that attribute somewhere in it.
        3) The find_string tool returns back a dictionary that contains a id that describes the flow, the request that 
        made that flow and the response to the request. This information should help you determine how the string you 
        searched is used. Determine what other attributes are of note in that flow. Pay particularily attention to any
        formdata or json in the request as you need to figure out where each attribute comes from if it was not provided.
        4) If you believe you have all the information that is needed to make a REST request for a flow, you should call
        'create_documentation' tool. You need to provide the flow id and a string that contains any other information
        that you are aware of that would be critical to make that call. This will return markdown to you.
        5) Continue all of the steps until you have all of the information you think you need to complete the user's goal
         - if you discover a new attribute that you don't know EXACTLY how you get it. Please search for it unless it is a basic instruction (i.e. 'submit')
        6) Once you are done, return a quick text based walkthrough on how to achieve the goal with the REST requests.
        7) If you ever discover information that is new and does not currently exist in the documentation - you can call
        `update_documentation` to add it to the documentation. You need to provide the markdown path and the extra 
        information
        A dictionary from data to value that we currently have is {self._existing_information} 
        i.e. username: test@gmail.com means that the username used in the flow data is test@gmail.com

        The user's goal is {self._goal}.
        You should do everything in your power to get all of the information needed to solve the user's goal.
        Make sure you call create_documentation for all flows that are needed. If you need to make a REST call to a 
        unique URL, there should be a documentation page for the flow that represents that.
                """

        # Below are all of the tools that we use - if I spent more time on this, I'd add a response schema to all of the tools
        # I would also clean this up, i'm not a huge fan of the general google tool objects as I feel like they are overcomplicated.
        find_str_function = types.FunctionDeclaration(
            name="find_string",
            description="Find a string in any of the mitm flows",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "search_str": types.Schema(
                        type=types.Type.STRING,
                        description="The EXACT string you are looking for in any of the flows.",
                    ),
                },
                required=["search_str"],
            ),
        )
        find_str_tool = types.Tool(function_declarations=[find_str_function])
        create_docs_function = types.FunctionDeclaration(
            name="create_documentation",
            description="Create documentation for a specific flow",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "flow_id": types.Schema(
                        type=types.Type.STRING,
                        description="The flow id of the flow that you want to make documentation for.",
                        enum=[flow["id"] for flow in self._flow_data],
                    ),
                    "extra_information": types.Schema(
                        type=types.Type.TYPE_UNSPECIFIED,
                        description="Any relevant information that will be helpful for making the docs. Including where you get specific attributes from.",
                    ),
                },
                required=["flow_id", "extra_information"],
            ),
        )
        create_docs_tool = types.Tool(function_declarations=[create_docs_function])
        update_docs_function = types.FunctionDeclaration(
            name="update_documentation",
            description="Update documentation for a specific flow",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "markdown_path": types.Schema(
                        type=types.Type.STRING,
                        description="The path of the markdown that already exists.",
                    ),
                    "extra_information": types.Schema(
                        type=types.Type.TYPE_UNSPECIFIED,
                        description="Any relevant information that will be helpful for making the docs. Including where you get specific attributes from.",
                    ),
                },
                required=["markdown_path", "extra_information"],
            ),
        )
        update_docs_tool = types.Tool(function_declarations=[update_docs_function])

        # Again in a real system this would be better, these should likely be Contents objects that contain the role
        # of the text and contain the thinking.
        content = [types.Part.from_text(text=prompt)]
        while True:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=content,
                config=types.GenerateContentConfig(
                    tools=[create_docs_tool, find_str_tool, update_docs_tool]
                ),
            )
            if not response.function_calls:
                return response.text
            content = content + [
                response.candidates[0].content
            ]  # Update the content history.
            for call in response.function_calls:
                # Call and store the results of the requested tools.
                if call.name == "find_string":
                    content.append(
                        types.Part.from_function_response(
                            name=call.name,
                            response={"results": self.find_string(**call.args)},
                        )
                    )
                if call.name == "create_documentation":
                    flow_id = call.args["flow_id"]
                    extra_information = call.args["extra_information"]
                    flow = [flow for flow in self._flow_data if flow["id"] == flow_id]
                    if len(flow) == 0:
                        print(flow_id)
                        content.append(
                            types.Part.from_function_response(
                                name=call.name,
                                response={
                                    "status": f"Failure - could not find id {flow_id}."
                                },
                            )
                        )
                    else:
                        self.create_documentation(flow[0], extra_information)
                        content.append(
                            types.Part.from_function_response(
                                name=call.name,
                                response={"status": "Success! Made documentation."},
                            )
                        )

    def create_api(self, user_description: str) -> None:
        """
        Create a python api using aiohttp that implements the markdown documentation.
        :param user_description: The description of what you want the api to do.
        """
        path = Path(self._markdown_folder)
        all_content: list[str] = []

        if not path.is_dir():
            return

        for file_path in path.iterdir():
            if file_path.is_file():
                all_content.append(file_path.read_text())
        content = "\n".join(all_content)
        prompt = f"""Create a Python api using aiohttp that implements the following apis:
            {content}
            
            Just give me the python code - no instructions on how to start it or run it, make it Object orientated.
            Add a __main__ in the file to run the api via inputs()
            Do NOT include codeblocks. You should just return the code as is.
            Prefer builtin libraries when possible. Prefer input() over getpass()
            The user gives the following information of their goals: {user_description}
            """
        api = self._client.models.generate_content(
            model="gemini-2.5-pro", contents=[prompt]
        )
        with open("api.py", "w") as f:
            f.write(api.text)


if __name__ == "__main__":
    MY_GEMINI_KEY = "KEY_HERE"
    MY_USERNAME = "USERNAME_HERE"
    MY_PASSWORD = "PASSWORD_HERE"
    agent = MitmAgent(
        goal="I want to get all of the REST requests needed to login to my account.",
        existing_information={"username": MY_USERNAME, "password": MY_PASSWORD},
        gemini_api_key=MY_GEMINI_KEY,
        ignore_existing=False,
    )
    agent.parse_flow_file("treasury_direct_flow")
    print(agent.solve())
    agent = MitmAgent(
        goal="I want to get all of the bonds in my account. Assume I am already logged in. I have provided some example data that i see on the bond summary page such as a bond's value.",
        existing_information={"Confirm #": "IAAAM", "Amount": "$500.00"},
        gemini_api_key=MY_GEMINI_KEY,
    )
    agent.parse_flow_file("treasury_direct_flow")
    print(agent.solve())
    agent = MitmAgent(
        goal="Given a bond issue date, issue value, and type - I want to get it's current value",
        existing_information={"Denomination": "500", "Total value": "$550.60"},
        gemini_api_key=MY_GEMINI_KEY,
        ignore_existing=True,
    )
    agent.parse_flow_file(
        "treasurydirect_value_lookup"
    )  # this is a separate flow for just getting the current value
    print(agent.solve())

    agent.create_api(
        "I want an api that can log me in and get me all of the ibonds that are currently in my treasury direct account OR will allow me to skip logging in and just enter in issue dates, starting values, and whatever other information i need to get a bonds current value."
    )
